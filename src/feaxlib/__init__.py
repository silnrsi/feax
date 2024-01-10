#!/usr/bin/env python3

import ufoLib2 as ufo
from collections import OrderedDict
from feaxlib.feax_parser import feaplus_parser
from xml.etree import ElementTree as et
import re

from silfont.core import execute

def getbbox(g):
    res = (65536, 65536, -65536, -65536)
    if g['outline'] is None:
        return (0, 0, 0, 0)
    for c in g['outline'].contours:
        for p in c['point']:
            if 'type' in p.attrib:      # any actual point counts
                x = float(p.get('x', '0'))
                y = float(p.get('y', '0'))
                res = (min(x, res[0]), min(y, res[1]), max(x, res[2]), max(y, res[3]))
    return res

class Glyph(object) :
    def __init__(self, name, advance=0, bbox=None):
        self.name = name
        self.anchors = {}
        self.is_mark = False
        self.advance = int(float(advance))
        self.bbox = bbox or (0, 0, 0, 0)

    def add_anchor(self, anchor):
        self.anchors[anchor.name] = (anchor.x, anchor.y)

    def decide_if_mark(self) :
        for a in self.anchors.keys():
            if a.startswith("_"):
                self.is_mark = True
                break

class FontInfo:
    def __init__(self, base):
        self.base = base

    def __getitem__(self, key):
        return getattr(self.base, key, None)

class Font(object) :
    def __init__(self, defines = None):
        self.glyphs = OrderedDict()
        self.classes = OrderedDict()
        self.all_aps = OrderedDict()
        self.fontinfo = {}
        self.kerns = {}
        self.defines = {} if defines is None else defines

    def readaps(self, f, omitaps=''):
        self.fontinfo = FontInfo(f.info)
        skipglyphs = set(f.lib.getval('public.skipExportGlyphs', []))
        for g in f.keys():
            if g in skipglyphs:
                continue
            ufo_g = f.get(g)
            adv = ufo_g.width
            bbox = ufo_g.getBounds()
            glyph = Glyph(g, advance=adv, bbox=bbox)
            self.glyphs[g] = glyph
            for a in ufo_g.anchors:
                if a.name not in omittedaps:
                    glyph.add_anchor(a)
                    self.all_aps.setdefault(a.name, []).append(glyph)
        self.classes = f.groups
        # repack flattened kerning
        for k, v in self.kerning.items():
            l, r = k
            if l in self.classes:
                l = "@" + l
            self.kerns.setdefault(l, {})[r] = v

    def read_classes(self, fname, classproperties=False):
        doc = et.parse(fname)
        for c in doc.findall('.//class'):
            class_name = c.get('name')
            m = re.search('\[(\d+)\]$', class_name)
            # support fixedclasses like make_gdl.pl via AP.pm
            if m:
                class_nm = class_name[0:m.start()]
                ix = int(m.group(1))
            else:
                class_nm = class_name
                ix = None
            cl = self.classes.setdefault(class_nm, [])
            for e in c.get('exts', '').split() + [""]:
                for g in c.text.split():
                    if g+e in self.glyphs or (e == '' and g.startswith('@')):
                        if ix:
                            cl.insert(ix, g+e)
                        else:
                            cl.append(g+e)
        if not classproperties:
            return
        for c in doc.findall('.//property'):
            for e in c.get('exts', '').split() + [""]:
                for g in c.text.split():
                    if g+e in self.glyphs:
                        cname = c.get('name') + "_" + c.get('value')
                        self.classes.setdefault(cname, []).append(g+e)
                    
    def make_classes(self, ligmode):
        for name, g in self.glyphs.items():
            # pull off suffix and make classes
            # TODO: handle ligatures
            base = name
            if ligmode is None or 'comp' not in ligmode or "_" not in name:
                pos = base.rfind('.')
                while pos > 0 :
                    old_base = base
                    ext = base[pos+1:]
                    base = base[:pos]
                    ext_class_nm = "c_" + ext
                    if base in self.glyphs and old_base in self.glyphs:
                        glyph_lst = self.classes.setdefault(ext_class_nm, [])
                        if not old_base in glyph_lst:
                            glyph_lst.append(old_base)
                            self.classes.setdefault("cno_" + ext, []).append(base)
                    pos = base.rfind('.')
            if ligmode is not None and "_" in name:
                comps = name.split("_")
                if "comp" in ligmode or "." not in comps[-1]:
                    base = comps.pop(-1 if "last" in ligmode else 0)
                    cname = base.replace(".", "_")
                    noname = "_".join(comps)
                    if base in self.glyphs and noname in self.glyphs:
                        glyph_lst = self.classes.setdefault("clig_"+cname, [])
                        if name not in glyph_lst:
                            glyph_lst.append(name)
                            self.classes.setdefault("cligno_"+cname, []).append(noname)
            if g.is_mark:
                self.classes.setdefault('GDEF_marks', []).append(name)
            else :
                self.classes.setdefault('GDEF_bases', []).append(name)

    def make_marks(self):
        for name, g in self.glyphs.items():
            g.decide_if_mark()

    def order_classes(self):
        # return ordered list of classnames as desired for FEA

        # Start with alphabetical then correct:
        #   1. Put classes like "cno_whatever" adjacent to "c_whatever"
        #   2. Classes can be defined in terms of other classes but FEA requires that
        #      classes be defined before they can be referenced.

        def sortkey(x):
            key1 = 'c_' + x[4:] if x.startswith('cno_') else x
            return (key1, x)

        classes = sorted(self.classes.keys(), key=sortkey)
        links = {}  # key = classname; value = list of other classes that include this one
        counts = {} # key = classname; value = count of un-output classes that this class includes
        for name in classes:
            y = [c[1:] for c in self.classes[name] if c.startswith('@')]  #list of included classes
            counts[name] = len(y)
            for c in y:
                links.setdefault(c, []).append(name)

        outclasses = []
        while len(classes) > 0:
            foundone = False
            for name in classes:
                if counts[name] == 0:
                    foundone = True
                    # output this class
                    outclasses.append(name)
                    classes.remove(name)
                    # adjust counts of classes that include this one
                    if name in links:
                        for n in links[name]:
                            counts[n] -= 1
                    # It may now be possible to output some we skipped earlier,
                    # so start over from the beginning of the list
                    break
            if not foundone:
                # all remaining classes include un-output classes and thus there is a loop somewhere
                raise ValueError("Class reference loop(s) found: " + ", ".join(classes))
        return outclasses

    def addComment(self, parser, text):
        cmt = parser.ast.Comment("# " + text, location=None)
        cmt.pretext = "\n"
        parser.add_statement(cmt)

    def append_classes(self, parser):
        # normal glyph classes
        self.addComment(parser, "Main Classes")
        for name in self.order_classes():
            gc = parser.ast.GlyphClass(None, location=None)
            for g in self.classes[name] :
                gc.append(g)
            gcd = parser.ast.GlyphClassDefinition(name, gc, location=None)
            parser.add_statement(gcd)
            parser.define_glyphclass(name, gcd)

    def _addGlyphsToClass(self, parser, glyphs, gc, anchor, definer):
        if len(glyphs) > 1:
            val = parser.ast.GlyphClass(glyphs, location=None)
        else :
            val = parser.ast.GlyphName(glyphs[0], location=None)
        classdef = definer(gc, anchor, val, location=None)
        gc.addDefinition(classdef)
        parser.add_statement(classdef)

    def append_positions(self, parser):
        # create base and mark classes, add to fea file dicts and parser symbol table
        bclassdef_lst = []
        mclassdef_lst = []
        self.addComment(parser, "Positioning classes and statements")
        for ap_nm, glyphs_w_ap in self.all_aps.items() :
            self.addComment(parser, "AP: " + ap_nm)
            # e.g. all glyphs with U AP
            if not ap_nm.startswith("_"):
                if any(not x.is_mark for x in glyphs_w_ap):
                    gcb = parser.set_baseclass(ap_nm)
                    parser.add_statement(gcb)
                if any(x.is_mark for x in glyphs_w_ap):
                    gcm = parser.set_baseclass(ap_nm + "_MarkBase")
                    parser.add_statement(gcm)
            else:
                gc = parser.set_markclass(ap_nm)

            # create lists of glyphs that use the same point (name and coordinates)
            # that can share a class definition
            anchor_cache = OrderedDict()
            markanchor_cache = OrderedDict()
            for g in glyphs_w_ap:
                p = g.anchors[ap_nm]
                if g.is_mark and not ap_nm.startswith("_"):
                    markanchor_cache.setdefault(p, []).append(g.name)
                else:
                    anchor_cache.setdefault(p, []).append(g.name)

            if ap_nm.startswith("_"):
                for p, glyphs_w_pt in anchor_cache.items():
                    anchor = parser.ast.Anchor(p[0], p[1], location=None)
                    self._addGlyphsToClass(parser, glyphs_w_pt, gc, anchor, parser.ast.MarkClassDefinition)
            else:
                for p, glyphs_w_pt in anchor_cache.items():
                    anchor = parser.ast.Anchor(p[0], p[1], location=None)
                    self._addGlyphsToClass(parser, glyphs_w_pt, gcb, anchor, parser.ast.BaseClassDefinition)
                for p, glyphs_w_pt in markanchor_cache.items():
                    anchor = parser.ast.Anchor(p[0], p[1], location=None)
                    self._addGlyphsToClass(parser, glyphs_w_pt, gcm, anchor, parser.ast.BaseClassDefinition)

#TODO: provide more argument info

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("infile", help="Input UFO or file")
    parser.add_argument("-i", "--input", required=True, help='Fea file to merge')
    parser.add_argument("-o", "--output", help='Output fea file')
    parser.add_argument("-c", "--classfile", help='Classes file')
    parser.add_argument("-L", "--ligmode", help='Parse ligatures: last - use last element as class name, first - use first element as class name, lastcomp, firstcomp - final variants are part of the component not the whole ligature')
    parser.add_argument("-D", "--define", action="append", help='Add option definition to pass to fea code --define=var=val')
    parser.add_argument("--classprops", action="store_true", help='Include property elements from classes file')
    parser.add_argument("--omitaps", default='', help='names of attachment points to omit (comma- or space-separated)')
    args = parser.parse_args()

    f = ufoLib2.Font.open(args.infile)
    defines = dict(x.split('=') for x in args.define) if args.define else {}
    res = feax_get_features(f, feaxfile=args.input, omitaps=args.omitaps, defines=defines,
                            classfile=args.classfile, classprops = args.classprops, ligmode=args.ligmode)
    if args.output :
        with open(args.output, "w") as of :
            of.write(res)


def feax_get_features(font, feaxfile=None, omitaps='', defines={}, classfile=None, classprops=False, ligmode=None):
    feafont = Font(defines)
    feafont.readaps(font, omitaps)
    feafont.make_marks()
    feafont.make_classes(ligmode)
    if classfile is not None:
        feafont.read_classes(classfile, classprops)
    p = feaplus_parser(None, feafont.glyphs, feafont.fontinfo, feafont.kerns, feafont.defines)
    doc = p.parse()
    feafont.append_classes(p)
    feafont.append_positions(p)
    if feaxfile is not None:
        doc = p.parse(feaxfile)
    res = doc.asFea()
    return res

if __name__ == '__main__': main()

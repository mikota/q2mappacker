from gooey import Gooey, GooeyParser
import re
import zipfile
import os
import io
from PIL import Image

class MapPacker:
    def __init__(self):
        self.progress = 0
        self.total = 0
        self.texture_names = set()
        self.skybox_name = ""
        self.zf: zipfile.ZipFile = None
        self.opts = None
    def extract_textures(self, filepath: str):
        found_skybox = False
        texture_pattern = re.compile(r"\(.*?\) \(.*?\) \(.*?\) (\S+) .*")
        skybox_pattern = re.compile(r'"sky" "(.*?)"') 
        with open(filepath, "r") as f:
            for line in f:
                m = texture_pattern.match(line)
                if m:
                    self.texture_names.add(m.group(1))
                elif not found_skybox:
                    m = skybox_pattern.match(line)
                    if m:
                        self.skybox_name = m.group(1)
                        found_skybox = True

    def pack_skybox(self):
        suffixes = ["ft", "bk", "lf", "rt", "up", "dn"]
        extensions = [
            ("pcx", True),
            ("tga", self.opts.tga),
            ("jpg", self.opts.jpg)
        ]
        for extension, should_pack in extensions:
            if not should_pack: continue
            for suffix in suffixes:
                skybox_path = f"{self.opts.moddir}/env/{self.skybox_name}{suffix}.{extension}"
                if os.path.exists(skybox_path):
                    self.zf.write(skybox_path, f"env/{self.skybox_name}{suffix}.{extension}")
                    print(f"Packed {self.skybox_name}{suffix}.{extension}")
                else:
                    print(f"Could not find {self.skybox_name}{suffix}.{extension}")

    def pack_textures(self):
        extensions = [
            ("wal", self.opts.wal),
            ("jpg", self.opts.jpg),
            ("png", self.opts.png),
            ("tga", self.opts.tga)
        ]
        for extension, should_pack in extensions:
            if not should_pack: continue
            for texture_name in self.texture_names:
                texture_path = f"{self.opts.moddir}/textures/{texture_name}.{extension}"
                if os.path.exists(texture_path):
                    if extension == "png" and self.opts.convpng:
                        print(f"Converting {texture_name}.png to jpg", end=" ")
                        img = Image.open(texture_path)
                        img = img.convert("RGB")
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="JPEG")
                        self.zf.writestr(f"textures/{texture_name}.jpg", img_bytes.getvalue())
                        print(f"-> Packing {texture_name}.jpg")
                    elif extension == "tga" and self.opts.convtga:
                        print(f"Converting {texture_name}.tga to png", end=" ")
                        img = Image.open(texture_path)
                        img = img.convert("RGBA")
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format="PNG")
                        self.zf.writestr(f"textures/{texture_name}.png", img_bytes.getvalue())
                        print(f"-> Packing {texture_name}.png")
                    else:
                        self.zf.write(texture_path, f"textures/{texture_name}.{extension}")
                        print(f"Packed {texture_name}.{extension}")
                else:
                    print(f"Could not find {texture_name}.{extension}")
            


@Gooey(tabbed_groups=True, program_name="q2mappacker")
def main():
    parser = GooeyParser()

    parser.add_argument(
        "--sourcemap", widget="FileChooser", help="The original .map file")
    parser.add_argument(
        "--bsp", widget="FileChooser", help="The compiled .bsp file"
    )
    parser.add_argument(
        "-moddir", widget="DirChooser", help="baseq2, or action for aq2, etc")
    parser.add_argument(
        "-o", "--output", widget="FileSaver", help="Should be mapname.pkz or mapname.zip")

    parser.add_argument(
        "-c", "--compress", action="store_true", help="zlib's implementation of deflated compression", default=True
    )

    tex_opts = parser.add_argument_group("Options")
    tex_opts.add_argument(
        "-m", "--packsourcemap", help="Pack original .map file", action="store_true")
    tex_opts.add_argument(
        "-w", "--wal", action="store_true", help="Pack wals", default=True)
    tex_opts.add_argument(
        "-j", "--jpg", action="store_true", help="Pack jpgs")
    tex_opts.add_argument(
        "-p", "--png", action="store_true", help="Pack pngs")
    tex_opts.add_argument(
        "-t", "--tga", action="store_true", help="Pack tgas")
    tex_opts.add_argument(
        "--convpng", action="store_true", help="Convert png to jpg")
    tex_opts.add_argument(
        "--convtga", action="store_true", help="Convert tga to png")

    opts = parser.parse_args()
    packer = MapPacker()
    packer.opts = opts
    packer.extract_textures(opts.sourcemap)
    packer.total = len(packer.texture_names) * [opts.wal, opts.jpg, opts.png, opts.tga].count(True) + 6
    base_mapname = os.path.basename(opts.sourcemap).split(".")[0]
    compression = zipfile.ZIP_DEFLATED if opts.compress else zipfile.ZIP_STORED
    compression_level = 9 if opts.compress else 0
    with zipfile.ZipFile(opts.output, "w", compression=compression, compresslevel=compression_level) as zf:
        packer.zf = zf
        if opts.packsourcemap:
            zf.write(opts.sourcemap, f"maps/{base_mapname}.map")
        if opts.bsp:
            zf.write(opts.bsp, f"maps/{base_mapname}.bsp")
        if packer.skybox_name:
            packer.pack_skybox()
        packer.pack_textures()
        print("Done")

if __name__ == '__main__':
    main()
    
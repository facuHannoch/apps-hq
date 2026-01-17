#!/usr/bin/env python3




from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


DEFAULT_MODEL = "gemini-2.5-flash-image"
DEFAULT_PUBLIC_DIR = "web/public"

# Output contract relative to public dir
OUT_ICON_512 = Path("icons/icon-512.png")
OUT_ICON_192 = Path("icons/icon-192.png")
OUT_APPLE = Path("icons/apple-touch-icon.png")
OUT_FAVICON = Path("favicon.ico")
OUT_OG = Path("og/og.png")


def fail(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def run_magick(args: list[str]) -> None:
    """
    Runs ImageMagick in a portable way.
    Prefers `magick` (Windows/IM7) then `convert` (Linux/IM6/IM7).
    """
    magick = which("magick")
    if magick:
        full = [magick] + args
    else:
        convert = which("convert")
        if convert:
            full = [convert] + args
        else:
            fail(
                "ImageMagick not found. Install `imagemagick` so `magick` or `convert` is available."
            )
    subprocess.run(full, check=True)


def read_text_file(path: Path) -> str:
    if not path.is_file():
        fail(f"Input file not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")

DEFAULT_PROMPT="""
Create a high-quality square logo icon for this application.
Style: clean, modern, simple, readable at small sizes.
Avoid text in the logo.
Prefer a flat/icon style with strong silhouette.
Return a single image.
"""

DEFAULT_ICON_PROMPT="""
Use the provided image to generate a icon for the website (will be converted to favicon format later)
Make it simpler, remove texts, but keep the essence of the logo.
"""

def generate_logo_png(
    api_key: str,
    model: str,
    prompt: str,
    out_path: Path,
    overwrite: bool,
    debug_json_path: Path | None,
) -> None:
    if out_path.exists() and not overwrite:
        print(f"Logo already exists, skipping generation: {out_path}")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        fail(f"Image API request failed: HTTP {resp.status_code} — {resp.text[:300]}")

    data = resp.json()

    if debug_json_path:
        debug_json_path.parent.mkdir(parents=True, exist_ok=True)
        debug_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Find the first inlineData image part
    try:
        parts = data["candidates"][0]["content"]["parts"]
        image_data_b64 = next(
            p["inlineData"]["data"] for p in parts if "inlineData" in p
        )
    except Exception:
        # keep a small hint for debugging
        fail("Could not find inline image data in API response (unexpected format).")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(image_data_b64))
    print(f"Wrote logo: {out_path}")


def generate_icon_from_logo(
    api_key: str,
    model: str,
    prompt: str,
    logo_path: Path,
    out_path: Path,
    overwrite: bool,
    debug_json_path: Path | None,
) -> None:
    """Generate a simplified icon from an existing logo image."""
    if out_path.exists() and not overwrite:
        print(f"Icon already exists, skipping generation: {out_path}")
        return

    if not logo_path.exists():
        fail(f"Logo file not found: {logo_path}")

    # Read and encode the logo image
    logo_bytes = logo_path.read_bytes()
    logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": logo_b64,
                        }
                    },
                ]
            }
        ]
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        fail(f"Icon API request failed: HTTP {resp.status_code} — {resp.text[:300]}")

    data = resp.json()

    if debug_json_path:
        debug_json_path.parent.mkdir(parents=True, exist_ok=True)
        icon_debug_path = debug_json_path.parent / "last_icon_response.json"
        icon_debug_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Find the first inlineData image part
    try:
        parts = data["candidates"][0]["content"]["parts"]
        image_data_b64 = next(
            p["inlineData"]["data"] for p in parts if "inlineData" in p
        )
    except Exception:
        fail("Could not find inline image data in API response (unexpected format).")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(image_data_b64))
    print(f"Wrote icon: {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Generate logo + icons + OG image into the app's public directory."
    )
    p.add_argument(
        "doc",
        type=str,
        help="Path to project doc file to feed the model (e.g. DESIGN.md).",
    )
    p.add_argument(
        "--public-dir",
        default=DEFAULT_PUBLIC_DIR,
        help="App public directory (default: web/public).",
    )
    p.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Image model (default: {DEFAULT_MODEL}).",
    )
    p.add_argument(
        "--api-key-env", default="IMAGE_AI_API_KEY", help="Env var containing API key."
    )
    p.add_argument(
        "--logo-out",
        default="ops/.cache/logo.png",
        help="Where to store the generated base logo (png).",
    )
    p.add_argument(
        "--overwrite-logo",
        action="store_true",
        help="Regenerate logo even if it exists.",
    )
    p.add_argument(
        "--icon-out",
        default="ops/.cache/icon.png",
        help="Where to store the generated icon based on the base logo.",
    )
    p.add_argument(
        "--overwrite-assets",
        action="store_true",
        help="Overwrite published assets in public dir.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not call API or write outputs; just print actions.",
    )
    p.add_argument(
        "--debug-json",
        default="ops/.cache/last_response.json",
        help="Write last API response JSON here.",
    )
    p.add_argument(
        "--custom-prompt",
        default=DEFAULT_PROMPT,
        help="Pass a custom prompt to define how the ai logo will be generated"
    )
    p.add_argument(
        "--custom-icon-prompt",
        default=DEFAULT_ICON_PROMPT,
        help="Pass a custom prompt to define how the icon will be generated"
    )
    args = p.parse_args()

    doc_path = Path(args.doc)
    public_dir = Path(args.public_dir)
    logo_path = Path(args.logo_out)
    icon_path = Path(args.icon_out)
    debug_json_path = Path(args.debug_json) if args.debug_json else None
    file_path = Path(__file__)

    # Validate directories
    if not public_dir.exists():
        fail(
            f"public dir does not exist: {public_dir} (did you run create-next-app in web/?)"
        )

    api_key = os.getenv(args.api_key_env)
    if not api_key:
        load_dotenv(f"{file_path}/.env")
        api_key = os.getenv(os.getenv("IMAGE_AI_API_KEY"))
    if not api_key and not args.dry_run:
        fail(f"Missing API key env var: {args.api_key_env}")

    doc = read_text_file(doc_path)

    prompt = f"""

{args.custom_prompt}

PROJECT DOCS:
---
{doc}
---
""".strip()


# solid, flat, unlit, green (#00b140) background

# Minimal flat icon, single solid color foreground, no shadows, no gradients, no textures, no background elements. Centered symbol only. Solid background color #00b140. Vector-like style, thick strokes, high contrast.

# background must be exactly #ff00ff.


# Don't use colors that confuse with black.
# solid, flat, unlit, pure black (#000000) background. This background should apply to all parts except the icon itself. If the logo is a circular design, do not make a circle with only the inner part with this background: make all that is external to the icon have the same background.


    icon_prompt = f"""

{args.custom_icon_prompt}

solid, flat, unlit background. This background should apply to all parts except the icon itself. If the logo is a circular design, do not make a circle with only the inner part with this background: make all that is external to the icon have the same background.
Use pure black (#000000) background.
No anti-aliasing against the background. No soft edges. No drop shadow. Hard edges.

"""


    if args.dry_run:
        print("DRY RUN")
        print(f"Would generate logo to: {logo_path}")
        print(f"Would generate icon out of logo ({logo_path}) to: {icon_path}")
    else:
        generate_logo_png(
            api_key=api_key,
            model=args.model,
            prompt=prompt,
            out_path=logo_path,
            overwrite=args.overwrite_logo,
            debug_json_path=debug_json_path,
        )
        # Generate simplified icon from the base logo
        generate_icon_from_logo(
            api_key=api_key,
            model=args.model,
            prompt=icon_prompt,
            logo_path=logo_path,
            out_path=icon_path,
            overwrite=True,
            debug_json_path=debug_json_path,
        )

    # Published outputs
    out_icon_512 = public_dir / OUT_ICON_512
    out_icon_192 = public_dir / OUT_ICON_192
    out_apple = public_dir / OUT_APPLE
    out_favicon = public_dir / OUT_FAVICON
    out_og = public_dir / OUT_OG

    if args.dry_run:
        print(
            f"Would write: {out_icon_512}, {out_icon_192}, {out_apple}, {out_favicon}, {out_og}"
        )
        return

    # Overwrite policy
    def should_write(path: Path) -> bool:
        return args.overwrite_assets or (not path.exists())

    # Ensure dirs
    (public_dir / "icons").mkdir(parents=True, exist_ok=True)
    (public_dir / "og").mkdir(parents=True, exist_ok=True)

    # 512
    if should_write(out_icon_512):
        run_magick([str(logo_path), "-resize", "512x512", str(out_icon_512)])
        print(f"Wrote: {out_icon_512}")

    # 192
    if should_write(out_icon_192):
        run_magick([str(logo_path), "-resize", "192x192", str(out_icon_192)])
        print(f"Wrote: {out_icon_192}")

    # Apple touch icon (remove alpha onto white for safety)
    if should_write(out_apple):
        run_magick(
            [
                str(logo_path),
                "-resize",
                "180x180",
                "-background",
                "white",
                "-alpha",
                "remove",
                "-alpha",
                "off",
                str(out_apple),
            ]
        )
        print(f"Wrote: {out_apple}")

    # Favicon multi-size ICO
    if should_write(out_favicon):
        # Create a temp transparent icon without modifying the original
        temp_icon = icon_path.parent / f"temp_{icon_path.name}"

        # Make the green background transparent
        run_magick([str(icon_path), "-fuzz", "2%", "-transparent", "#000000", str(temp_icon)])

        # 2) Create multi-size ICO, KEEP alpha
        run_magick(
            [
                str(temp_icon),
                "-define", "icon:auto-resize=256,128,64,48,32,16",
                str(out_favicon),
            ]
        )
        
        # Create preview icon to validate the design
        run_magick([f"{str(icon_path)}[0]", "-resize", "16x16", "check-16.png"])

        if temp_icon.exists():
            temp_icon.unlink()
        print(f"Wrote: {out_favicon}")


        # run_magick([str(icon_path), "-transparent", "#00b140", str(temp_icon)])
        # # Flatten onto white background to remove transparency, then convert to .ico
        # run_magick(
        #     [
        #         str(temp_icon),
        #         "-background",
        #         "white",
        #         "-alpha",
        #         "remove",
        #         "-alpha",
        #         "off",
        #         "-define",
        #         "icon:auto-resize=256,128,64,48,32,16",
        #         str(out_favicon),
        #     ]
        # )
        # # Clean up temp file
        # if temp_icon.exists():
        #     temp_icon.unlink()
        # print(f"Wrote: {out_favicon}")

    # OG image (centered logo on white background)
    if should_write(out_og):
        run_magick(
            [
                "-size",
                "1200x630",
                "xc:white",
                "(",
                str(logo_path),
                "-resize",
                "460x460",
                ")",
                "-gravity",
                "center",
                "-composite",
                str(out_og),
            ]
        )
        print(f"Wrote: {out_og}")

    print("Done.")


if __name__ == "__main__":
    main()

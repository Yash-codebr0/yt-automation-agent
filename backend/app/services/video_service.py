import os
import math
import subprocess
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Niche Theme Presets
# ---------------------------------------------------------------------------
THEMES = {
    "ai": {
        "name": "Cyber Intelligence",
        "primary": (6, 182, 212),       # Cyan
        "secondary": (168, 85, 247),    # Violet
        "accent": (244, 63, 94),        # Rose
        "bg_gradient": ((10, 15, 30), (20, 10, 40)),
        "badge_bg": (6, 182, 212, 220),
        "badge_text": (255, 255, 255),
        "tag": "⚡ AI MATRIX 2026",
    },
    "programming": {
        "name": "Dev Terminal",
        "primary": (52, 211, 153),      # Emerald
        "secondary": (96, 165, 250),    # Blue
        "accent": (251, 191, 36),       # Amber
        "bg_gradient": ((12, 18, 28), (15, 30, 25)),
        "badge_bg": (16, 185, 129, 220),
        "badge_text": (255, 255, 255),
        "tag": "💻 DEV ARCHITECTURE",
    },
    "car": {
        "name": "Apex Motorsport",
        "primary": (255, 75, 30),       # High-octane Orange/Red
        "secondary": (250, 204, 21),    # Speed Yellow
        "accent": (56, 189, 248),       # Turbo Cyan
        "bg_gradient": ((18, 8, 8), (30, 12, 10)),
        "badge_bg": (255, 75, 30, 230),
        "badge_text": (255, 255, 255),
        "tag": "🏎️ CINEMATIC MOTORSPORT",
    },
    "finance": {
        "name": "Gold & Capital",
        "primary": (234, 179, 8),       # Gold
        "secondary": (16, 185, 129),    # Emerald Profit
        "accent": (244, 63, 94),        # Loss Rose
        "bg_gradient": ((12, 20, 16), (20, 24, 15)),
        "badge_bg": (202, 138, 4, 220),
        "badge_text": (255, 255, 255),
        "tag": "📈 CAPITAL INSIDER",
    },
    "gaming": {
        "name": "Neon Arcade",
        "primary": (236, 72, 153),      # Neon Pink
        "secondary": (139, 92, 246),    # Electric Purple
        "accent": (34, 211, 238),       # Bright Cyan
        "bg_gradient": ((18, 10, 28), (28, 10, 25)),
        "badge_bg": (217, 70, 239, 220),
        "badge_text": (255, 255, 255),
        "tag": "🎮 NEXT-GEN GAMING",
    },
    "fitness": {
        "name": "Kinetic Energy",
        "primary": (245, 158, 11),      # Amber
        "secondary": (16, 185, 129),    # Emerald
        "accent": (239, 68, 68),        # Crimson
        "bg_gradient": ((20, 18, 12), (28, 20, 15)),
        "badge_bg": (245, 158, 11, 220),
        "badge_text": (255, 255, 255),
        "tag": "🔥 PEAK PERFORMANCE",
    },
    "general": {
        "name": "Modern Slate",
        "primary": (147, 51, 234),      # Purple
        "secondary": (59, 130, 246),    # Blue
        "accent": (236, 72, 153),       # Pink
        "bg_gradient": ((15, 15, 25), (25, 20, 35)),
        "badge_bg": (147, 51, 234, 220),
        "badge_text": (255, 255, 255),
        "tag": "🎬 EMPIRE CINEMA",
    }
}

EMPHASIS_WORDS = {
    "SECRET", "TRUTH", "NEW", "TOP", "BEST", "WARNING", "MASSIVE", "HOW",
    "INSANE", "BREAKING", "FUTURE", "FAST", "MONEY", "STOP", "AI", "ULTIMATE",
    "REVEALED", "100%", "GAME-CHANGING", "NEVER", "GUIDE", "PRO", "EVERYONE"
}


class VideoService:

    @classmethod
    def get_niche_theme(cls, niche: str) -> Dict[str, Any]:
        """Resolves the visual styling theme for a given niche."""
        niche_lower = (niche or "").lower()
        for key in ["ai", "programming", "car", "auto", "finance", "gaming", "fitness"]:
            if key in niche_lower:
                if key == "auto":
                    return THEMES["car"]
                return THEMES[key]
        return THEMES["general"]

    @classmethod
    def build_storyboard_scenes(
        cls,
        script: Dict[str, str],
        trend_title: str,
        niche: str
    ) -> List[Dict[str, Any]]:
        """Segments the script into 4 dynamic storyboard scenes with phase cues."""
        hook_text = (script.get("hook") or trend_title or f"Top {niche} Update").strip()
        body_text = (script.get("body") or f"Discover the ultimate {niche} breakthroughs happening right now.").strip()
        cta_text = (script.get("cta") or "Subscribe and like for daily updates!").strip()

        # Split body into two distinct beats
        body_sentences = [s.strip() for s in body_text.replace("\n", " ").split(".") if len(s.strip()) > 3]
        if len(body_sentences) >= 2:
            mid = len(body_sentences) // 2
            beat1 = ". ".join(body_sentences[:mid]) + "."
            beat2 = ". ".join(body_sentences[mid:]) + "."
        elif len(body_sentences) == 1:
            beat1 = body_sentences[0] + "."
            beat2 = "Here is what this means for your strategy moving forward."
        else:
            beat1 = "Key architectural patterns and core advantages."
            beat2 = "Execution details and performance metrics."

        return [
            {
                "id": "scene_hook",
                "phase": "⚡ HOOK",
                "headline": hook_text,
                "subtext": "Attention Grabber",
                "zoom_dir": 1.0,  # Zoom in
                "weight": 0.25
            },
            {
                "id": "scene_beat1",
                "phase": "💡 CORE BREAKDOWN",
                "headline": beat1,
                "subtext": "Key Insights",
                "zoom_dir": -1.0, # Pan & drift
                "weight": 0.28
            },
            {
                "id": "scene_beat2",
                "phase": "🔥 THE REVELATION",
                "headline": beat2,
                "subtext": "Critical Deep Dive",
                "zoom_dir": 1.0,  # Zoom in focus
                "weight": 0.27
            },
            {
                "id": "scene_cta",
                "phase": "🎯 NEXT ACTION",
                "headline": cta_text,
                "subtext": "Join the Movement",
                "zoom_dir": 0.5,
                "weight": 0.20
            }
        ]

    @classmethod
    def render_video(
        cls,
        project_id: str,
        thumb_path: str,
        voice_path: str,
        output_path: str,
        script: Dict[str, str],
        trend_title: str,
        niche: str,
        aspect_ratio: str = "16:9",  # "16:9" or "9:16"
        fps: int = 24
    ) -> Dict[str, Any]:
        """Renders an enhanced cinematic MP4 video with multi-scene storyboarding,
        kinetic subtitles, dynamic audio beat sync, progress meters, and niche themes."""
        
        # Determine canvas dimensions
        if aspect_ratio == "9:16":
            width, height = 720, 1280
            is_vertical = True
        else:
            width, height = 1280, 720
            is_vertical = False

        theme = cls.get_niche_theme(niche)
        scenes = cls.build_storyboard_scenes(script, trend_title, niche)

        # Load and prepare base image
        if not os.path.exists(thumb_path):
            raise FileNotFoundError(f"Thumbnail background image missing: {thumb_path}")
        
        base_raw = Image.open(thumb_path).convert("RGB")
        base_image = base_raw.resize((width, height), Image.LANCZOS)

        # Try to import MoviePy
        try:
            from moviepy.editor import AudioFileClip, VideoClip
        except ImportError:
            from moviepy import AudioFileClip, VideoClip

        audio = None
        clip = None
        duration = 8.0

        if voice_path and os.path.exists(voice_path):
            try:
                audio = AudioFileClip(voice_path)
                duration = getattr(audio, "duration", 8.0) or 8.0
            except Exception as audio_err:
                print(f"Voiceover decode warning: {audio_err}. Rendering preview.")
                audio = None
                duration = 8.0

        # Load typography fonts
        try:
            title_size = 46 if not is_vertical else 40
            badge_size = 24 if not is_vertical else 22
            title_font = ImageFont.truetype("arialbd.ttf", title_size)
            badge_font = ImageFont.truetype("arialbd.ttf", badge_size)
        except Exception:
            title_font = ImageFont.load_default()
            badge_font = ImageFont.load_default()

        # Text wrapping helper
        def wrap_text(text: str, font, max_w: int, max_lines: int = 3) -> List[str]:
            words = (text or "").split()
            lines, current = [], ""
            measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
            for word in words:
                probe = f"{current} {word}".strip()
                bbox = measure.textbbox((0, 0), probe, font=font)
                if bbox[2] <= max_w or not current:
                    current = probe
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)
            return lines[:max_lines]

        # Calculate scene time boundaries
        scene_boundaries = []
        accum = 0.0
        for s in scenes:
            scene_dur = duration * s["weight"]
            scene_boundaries.append((accum, accum + scene_dur, s))
            accum += scene_dur

        # Frame rendering function for MoviePy
        def make_frame(t):
            progress = max(0.0, min(1.0, t / max(duration, 0.1)))
            beat = (math.sin(t * math.pi * 3.5) + 1) / 2.0
            pulse_shake = math.sin(t * math.pi * 8.0) * 0.005

            # Identify active scene
            active_scene = scenes[-1]
            scene_progress = 0.0
            for start_t, end_t, sc in scene_boundaries:
                if start_t <= t <= end_t:
                    active_scene = sc
                    scene_progress = (t - start_t) / max(end_t - start_t, 0.01)
                    break

            # 1. Dynamic Ken Burns Camera Zoom & Pan
            zoom = 1.05 + 0.18 * scene_progress + 0.03 * beat + pulse_shake
            crop_w, crop_h = int(width / zoom), int(height / zoom)
            pan_x = int((width - crop_w) * (0.5 + 0.35 * math.sin(t * 1.1)))
            pan_y = int((height - crop_h) * (0.5 + 0.30 * math.cos(t * 0.9)))
            
            # Boundary clamps
            pan_x = max(0, min(width - crop_w, pan_x))
            pan_y = max(0, min(height - crop_h, pan_y))

            frame = base_image.crop((pan_x, pan_y, pan_x + crop_w, pan_y + crop_h)).resize((width, height), Image.LANCZOS)
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            # 2. Ambient Niche Glow & Vignette
            p_col = theme["primary"]
            s_col = theme["secondary"]
            
            # Top/bottom ambient gradients
            banner_h = 190 if not is_vertical else 300
            draw.rectangle((0, height - banner_h - 20, width, height), fill=(10, 12, 18, 220))
            draw.rectangle((0, 0, width, 90), fill=(10, 12, 18, 180))

            # Pulsing top & bottom neon accent lines
            neon_alpha = int(140 + 90 * beat)
            draw.rectangle((0, 0, width, 6), fill=(*p_col, neon_alpha))
            draw.rectangle((0, height - 8, width, height), fill=(*s_col, neon_alpha))

            # Diagonal dynamic light sweep
            sweep_pos = int((width + 400) * ((t * 0.6) % 1.0)) - 300
            draw.polygon(
                [(sweep_pos, 0), (sweep_pos + 100, 0), (sweep_pos + 300, height), (sweep_pos + 200, height)],
                fill=(255, 255, 255, 24)
            )

            # 3. Top Watermark & Phase Badge
            badge_x = 40
            badge_y = 30
            tag_label = f"{theme['tag']}  |  {active_scene['phase']}"
            tag_bbox = draw.textbbox((0, 0), tag_label, font=badge_font)
            tag_w = tag_bbox[2] - tag_bbox[0] + 32
            draw.rounded_rectangle((badge_x, badge_y, badge_x + tag_w, badge_y + 44), radius=10, fill=theme["badge_bg"])
            draw.text((badge_x + 16, badge_y + 8), tag_label, fill=theme["badge_text"], font=badge_font)

            # 4. Kinetic Subtitles & Typography
            max_text_width = width - 100
            wrapped_lines = wrap_text(active_scene["headline"], title_font, max_text_width, max_lines=3 if is_vertical else 2)
            
            start_y = height - banner_h + (30 if not is_vertical else 50)
            for line_idx, line in enumerate(wrapped_lines):
                line_y = start_y + line_idx * 52
                
                # Check for highlighted keywords in the line
                words = line.split()
                cur_x = 48
                for w in words:
                    clean_w = "".join(c for c in w if c.isalnum()).upper()
                    is_emp = clean_w in EMPHASIS_WORDS or any(char.isdigit() for char in clean_w)
                    
                    word_color = theme["primary"] if is_emp else (255, 255, 255)
                    # Text shadow
                    draw.text((cur_x + 2, line_y + 2), w + " ", fill=(0, 0, 0, 220), font=title_font)
                    # Main text
                    draw.text((cur_x, line_y), w + " ", fill=word_color, font=title_font)
                    
                    w_box = draw.textbbox((0, 0), w + " ", font=title_font)
                    cur_x += (w_box[2] - w_box[0])

            # 5. Real-Time Linear Progress Indicator Bar
            bar_y = height - 16
            bar_w = int(width * progress)
            draw.rectangle((0, bar_y, width, height - 8), fill=(255, 255, 255, 50))
            draw.rectangle((0, bar_y, bar_w, height - 8), fill=(*theme["primary"], 255))

            return np.array(Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB"))

        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            clip = VideoClip(make_frame, duration=duration)
            if audio:
                if hasattr(clip, "with_audio"):
                    clip = clip.with_audio(audio)
                else:
                    clip = clip.set_audio(audio)

            write_kwargs = {
                "fps": fps,
                "codec": "libx264",
                "remove_temp": True,
                "logger": None,
                "preset": "ultrafast",
                "ffmpeg_params": ["-crf", "22", "-pix_fmt", "yuv420p"]
            }

            if audio:
                write_kwargs["audio_codec"] = "aac"
                temp_audio = os.path.join(settings.MEDIA_DIR, f"temp_{project_id}_{aspect_ratio.replace(':', '_')}.m4a")
                write_kwargs["temp_audiofile"] = temp_audio
            else:
                write_kwargs["audio"] = False

            clip.write_videofile(output_path, **write_kwargs)

        finally:
            if clip:
                try:
                    clip.close()
                except Exception:
                    pass
            if audio:
                try:
                    audio.close()
                except Exception:
                    pass

        return {
            "output_path": output_path,
            "duration": round(duration, 2),
            "aspect_ratio": aspect_ratio,
            "resolution": f"{width}x{height}",
            "theme": theme["name"],
            "scenes_count": len(scenes)
        }

import os
import random
import json
from PIL import Image, ImageDraw, ImageFont
from tenacity import retry, stop_after_attempt, wait_exponential
from backend.app.core.config import settings

class OpenAIService:
    @staticmethod
    def get_client():
        if settings.is_openai_mock:
            return None
        from openai import OpenAI
        return OpenAI(api_key=settings.OPENAI_API_KEY)

    @classmethod
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _create_chat_completion_with_retry(cls, client, prompt, model="gpt-4o-mini", response_format=None):
        return client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_format
        )

    @classmethod
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _generate_thumbnail_with_retry(cls, client, prompt):
        return client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )

    @classmethod
    def generate_script(cls, niche: str, trend_title: str) -> dict:
        """Generates video title, hook, body, and CTA."""
        if settings.is_openai_mock:
            return cls._get_mock_script(niche, trend_title)
        
        client = cls.get_client()
        prompt = f"""
        You are a viral YouTube content writer. Generate a script for a video about '{trend_title}' in the niche '{niche}'.
        
        Respond with a JSON object containing exactly the following keys:
        - "title": A high-CTR, clickbaity YouTube video title.
        - "hook": The first 15 seconds of the video, designed to grab attention.
        - "body": The main script (around 150-200 words), engaging, informative, and fast-paced.
        - "cta": A strong call-to-action (CTA) to subscribe and like.
        
        Return ONLY valid JSON. No markdown formatting blocks.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI script error after retries: {e}")
            raise

    @classmethod
    def analyze_niche(cls, niche: str, trend_title: str) -> dict:
        """Scores a topic based on competition, estimated views, content difficulty."""
        if settings.is_openai_mock:
            return cls._get_mock_niche_analysis(niche, trend_title)
            
        client = cls.get_client()
        prompt = f"""
        Analyze this trending topic: '{trend_title}' for the niche '{niche}'.
        Evaluate the competition (0-100), estimated views potential (0-100), and content creation difficulty (0-100).
        Calculate an overall opportunity score (0-100) where higher is better.
        
        Respond with a JSON object containing exactly:
        - "competition": int
        - "estimated_views": int
        - "content_difficulty": int
        - "opportunity_score": int
        - "summary": string explaining the reasoning.
        
        Return ONLY valid JSON.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI niche analysis error after retries: {e}")
            raise

    @classmethod
    def generate_thumbnail_image(cls, script_title: str, save_path: str) -> str:
        """Generates a thumbnail using DALL-E or PIL fallback."""
        if settings.is_openai_mock:
            return cls._generate_mock_thumbnail(script_title, save_path)
            
        client = cls.get_client()
        prompt = f"A viral high-contrast YouTube thumbnail background, highly cinematic, 3d render, vibrant colors, representing: {script_title}. No text in the image."
        try:
            response = cls._generate_thumbnail_with_retry(client, prompt)
            image_url = response.data[0].url
            # Download and save the image
            import httpx
            with httpx.Client() as http_client:
                r = http_client.get(image_url)
                if r.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(r.content)
                    return save_path
            raise Exception("Failed to download generated image")
        except Exception as e:
            print(f"DALL-E thumbnail error after retries: {e}")
            raise


    @staticmethod
    def _generate_mock_thumbnail(title: str, save_path: str) -> str:
        """Draws a beautiful, modern text-overlay image using PIL."""
        # Create a blank image with a dark gradient-like background
        width, height = 1280, 720
        img = Image.new("RGB", (width, height), color=(15, 15, 20))
        draw = ImageDraw.Draw(img)

        # Draw a beautiful diagonal gradient/shape
        for i in range(width):
            r = int(15 + (i / width) * 45)
            g = int(15 + (i / width) * 20)
            b = int(25 + (i / width) * 75)
            for j in range(height):
                img.putpixel((i, j), (r, g, b))

        # Add decorative circular glowing shapes
        draw.ellipse([(-100, -100), (300, 300)], fill=(128, 90, 213, 100))
        draw.ellipse([(900, 400), (1400, 900)], fill=(221, 107, 32, 100))

        # Write text
        text_line1 = "YT EMPIRE"
        text_line2 = title[:24] + "..." if len(title) > 24 else title
        
        # Fallback drawing using default font
        draw.text((60, 200), text_line1, fill=(236, 201, 75), font=None, size=80)
        draw.text((60, 320), text_line2, fill=(255, 255, 255), font=None, size=60)
        draw.text((60, 450), "100% AUTOMATED BY AGENT", fill=(79, 209, 197), font=None, size=35)
        
        # Save image
        img.save(save_path, "JPEG")
        return save_path

    @staticmethod
    def _get_mock_script(niche: str, trend_title: str) -> dict:
        hooks = [
            f"Here is why {trend_title} is breaking the internet right now!",
            f"Think you know everything about {trend_title}? Think again.",
            f"The secret behind {trend_title} is finally out, and it changes everything.",
            f"This new update on {trend_title} is absolute madness!"
        ]
        
        ctas = [
            "If you want to stay ahead of the curve, hit that subscribe button right now!",
            "Subscribe for daily tech and finance hacks. See you in the next one!",
            "Drop a comment with your thoughts on this, and don't forget to like!",
            "Smash that subscribe button to join our growing community of builders!"
        ]

        if niche == "AI":
            body = (
                f"Artificial Intelligence is moving faster than ever, and '{trend_title}' is the perfect example. "
                "Developers and companies are racing to adopt these tools because they save hundreds of hours. "
                "If you are not leveraging this in your workflow today, you are falling behind. "
                "From automated code assistants to autonomous video generators, the AI landscape is shifting daily."
            )
        elif niche == "Programming":
            body = (
                f"In the software engineering space, '{trend_title}' is currently the hot topic. "
                "Clean architecture, type-safety, and lightning-fast developer experience are top priorities. "
                "Whether you are building microservices or a single-page app, understanding this concept is crucial. "
                "Let's dive into the code and see how it works under the hood."
            )
        elif niche == "Finance":
            body = (
                f"Markets are reacting strongly today, and '{trend_title}' is driving the momentum. "
                "Smart money is moving quickly into safe-haven assets and high-growth technology. "
                "With inflation rates shifting and federal announcements looming, keeping an eye on these indicators "
                "is critical to protect your portfolio and spot new opportunities."
            )
        elif any(word in niche.lower() for word in ("car", "auto", "automotive", "vehicle")):
            body = (
                f"Car edits live or die by motion, and '{trend_title}' needs a fast cinematic build. "
                "Open with a cold start sound, cut straight into a rolling shot, then sync every beat to a speed ramp. "
                "Use close-ups on headlights, wheels, badges, and exhaust before revealing the full car. "
                "Keep the captions short, punchy, and timed to transitions so the edit feels premium instead of like a slideshow."
            )
        else:  # Startups
            body = (
                f"Startups are all about scale and product-market fit. Right now, '{trend_title}' is showing how "
                "lean teams can outpace legacy corporations. By focusing on customer obsession and rapid iteration, "
                "founders are bootstrapping to millions in annual recurring revenue. "
                "Here is the playbook you can copy."
            )

        return {
            "title": f"The Truth About {trend_title} ({niche} Guide)",
            "hook": random.choice(hooks),
            "body": body,
            "cta": random.choice(ctas)
        }

    @staticmethod
    def _get_mock_niche_analysis(niche: str, trend_title: str) -> dict:
        comp = random.randint(30, 85)
        views = random.randint(45, 95)
        diff = random.randint(20, 70)
        opp = int((views * 2 + (100 - comp) + (100 - diff)) / 4)
        return {
            "niche": niche,
            "trend_title": trend_title,
            "competition_score": comp,
            "view_potential": views,
            "difficulty": diff,
            "opportunity_score": opp
        }

    # --- Phase 2: AI Agent Implementations ---

    @classmethod
    def research_competitors(cls, niche: str, trend_title: str) -> str:
        """Competitor Research Agent: analyzes competitor video angles and lengths."""
        if settings.is_openai_mock:
            return f"Competitor analysis for '{trend_title}': Identified 5 top videos in the '{niche}' niche. The top video has 1.2M views, uses an open loop hook, and spans 9:15. Competitor thumbnails focus on clean contrasting typography (yellow/white) with a human face on the right."
        
        client = cls.get_client()
        prompt = f"Analyze top competitor YouTube videos for the trend: '{trend_title}' in the niche '{niche}'. Identify common hooks, video length, structure patterns, visual angles, and themes."
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Competitor Research error: {e}")
            raise

    @classmethod
    def research_keywords(cls, niche: str, trend_title: str) -> list[str]:
        """Keyword Research Agent: compiles target tags and keywords."""
        if settings.is_openai_mock:
            return [f"{niche.lower()} trends", f"{trend_title.lower()} tutorial", f"autonomous {niche.lower()}", "coding ai agent", "startup strategy"]
        
        client = cls.get_client()
        prompt = f"""
        Provide a list of the top 8 high-volume YouTube search tags and keywords for the topic: '{trend_title}' in the niche '{niche}'.
        Respond with a JSON object containing exactly a key "keywords" which is a list of strings.
        Return ONLY valid JSON.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt, response_format={"type": "json_object"})
            data = json.loads(response.choices[0].message.content)
            return data.get("keywords", [])
        except Exception as e:
            print(f"Keyword Research error: {e}")
            raise

    @classmethod
    def research_audience(cls, niche: str, trend_title: str) -> str:
        """Audience Research Agent: analyzes demographic interest, pain points, and intent."""
        if settings.is_openai_mock:
            return f"Audience Profile for '{trend_title}': Demographics skew 82% male, 18-34 age group. Primary pain points: deployment complexity, APIs cost, lack of developer templates. Query search intent: 'how to build step-by-step'."
        
        client = cls.get_client()
        prompt = f"Identify the target YouTube audience demographics, pain points, search intent, and top questions for a video about '{trend_title}' in the niche '{niche}'."
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Audience Research error: {e}")
            raise

    @classmethod
    def generate_video_idea(cls, niche: str, trend_title: str, comp_research: str, kw_research: list[str]) -> str:
        """Idea Generator Agent: synthesizes research to write a high-CTR video concept and hook angle."""
        if settings.is_openai_mock:
            if any(word in niche.lower() for word in ("car", "auto", "automotive", "vehicle")):
                return f"{trend_title}: Cinematic Car Edit With Beat-Synced Speed Ramps"
            return f"The Truth about {trend_title}: Build Your Own Multi-Agent System in 10 Minutes"
        
        client = cls.get_client()
        prompt = f"""
        Generate a single highly engaging, high-CTR YouTube video title and core concept based on:
        Niche: {niche}
        Trend: {trend_title}
        Competitor Insights: {comp_research}
        Keywords to target: {', '.join(kw_research)}
        
        Provide only the title and a 1-sentence concept description.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Idea Generator error: {e}")
            raise

    @classmethod
    def fact_check_script(cls, niche: str, script_body: str) -> str:
        """Fact Checker Agent: cross-checks claims in the script."""
        if settings.is_openai_mock:
            return "Fact Checker Report: 100% verified. No false statistics or misleading statements detected. Tone is correct."
        
        client = cls.get_client()
        prompt = f"Review this script body for niche '{niche}' and check for false claims, inaccuracies, or unverified claims:\n\n{script_body}"
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Fact Checker error: {e}")
            raise

    @classmethod
    def review_script(cls, script_hook: str, script_body: str, script_cta: str) -> dict:
        """Script Reviewer Agent: scores hooks, body pacing, and CTA clickability."""
        if settings.is_openai_mock:
            return {
                "score": 87,
                "feedback": "Great hook with strong curiosity gap. The body is highly engaging. Recommendation: add a visual proof cue in the first 10 seconds to reduce early drop-offs."
            }
        
        client = cls.get_client()
        prompt = f"""
        Critique the pacing, retention hooks, and CTA of this YouTube script.
        Hook: {script_hook}
        Body: {script_body}
        CTA: {script_cta}
        
        Respond with a JSON object containing exactly:
        - "score": int (0-100)
        - "feedback": string containing critiques and actionable improvements.
        
        Return ONLY valid JSON.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Script Reviewer error: {e}")
            raise

    @classmethod
    def score_thumbnail(cls, image_path: str, script_title: str) -> dict:
        """Thumbnail Scorer Agent: scores visual appeal and clickability."""
        # Note: In mock/dev we mock it. In live, if GPT-4o keys are available, we can pass image data URL to completions API.
        if settings.is_openai_mock or not os.path.exists(image_path):
            return {
                "clickability_score": 89,
                "feedback": "Vibrant blue/cyan contrast is highly effective. Typography stands out. The yellow accent highlights the focus keyword."
            }
            
        client = cls.get_client()
        # Read image bytes and encode to base64
        import base64
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                
            prompt_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": f"You are a professional YouTube designer. Score this thumbnail visual design for the video title '{script_title}'. Evaluate readability, emotional trigger, clickability, and contrast. Return a JSON object with keys 'clickability_score' (int 0-100) and 'feedback' (string)."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded_string}"}
                        }
                    ]
                }
            ]
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=prompt_messages,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Thumbnail Scorer vision API error: {e}, falling back to description scoring")
            # Fallback text check if base64/vision fails
            return {
                "clickability_score": 75,
                "feedback": f"Could not perform visual vision check, but analyzed design prompt for title '{script_title}'. High contrast layouts are recommended."
            }

    @classmethod
    def verify_brand(cls, title: str, content: str) -> str:
        """Brand Consistency Agent: checks brand guidelines consistency."""
        if settings.is_openai_mock:
            return "Brand Consistency Report: Energetic, authoritative voice meets the 100% technical brand guidelines. Approved."
        
        client = cls.get_client()
        prompt = f"Check if this video title '{title}' and script content matches an authoritative, tech-savvy, educational brand kit guidelines:\n\n{content}"
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Brand Consistency error: {e}")
            raise

    @classmethod
    def optimize_retention(cls, script_body: str) -> str:
        """Retention Optimizer Agent: injects pacing, overlays, and sound instructions."""
        if settings.is_openai_mock:
            return "[0:00 - Fast push-in opener]\n[0:04 - Beat-synced flash cut]\n[0:08 - Whip pan transition]\n[0:12 - Caption punch-in]\n[0:18 - Speed ramp reveal]"
        
        client = cls.get_client()
        prompt = f"Suggest visual scene triggers, sound effects, text overlay timestamps, and zooming instructions to maximize viewer retention for this script body:\n\n{script_body}"
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Retention Optimizer error: {e}")
            raise

    @classmethod
    def generate_shorts(cls, script_body: str) -> dict:
        """Shorts Generator Agent: generates vertical 30-60s short script."""
        if settings.is_openai_mock:
            return {
                "title": "Build Agents Fast! 🚀",
                "hook": "Chatbots are dead, build stateful agents instead!",
                "body": "Traditional chatbots run linearly, but real world agent loops need memory and cycles. LangGraph solves this by introducing cyclic graphs in python.",
                "cta": "Like and subscribe for agent secrets!"
            }
        
        client = cls.get_client()
        prompt = f"""
        Condense this main script into a vertical YouTube Shorts format under 100 words.
        Respond with a JSON object containing exactly:
        - "title": clickbaity short title
        - "hook": 5-second attention grabber
        - "body": 30-second core value point
        - "cta": quick like/subscribe call
        
        Return ONLY valid JSON.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Shorts Generator error: {e}")
            raise

    @classmethod
    def translate_metadata(cls, title: str, description: str, tags: str) -> dict:
        """Translation Agent: translates title, description, and tags to Spanish."""
        if settings.is_openai_mock:
            return {
                "spanish_title": f"La Verdad sobre {title} (Guía Completa)",
                "spanish_description": f"En este video cubrimos todo acerca de {title}. No te lo pierdas.\n\nDescripción original: {description[:50]}...",
                "spanish_tags": f"ia, automatización, {tags}"
            }
        
        client = cls.get_client()
        prompt = f"""
        Translate this YouTube metadata into Spanish.
        Title: {title}
        Description: {description}
        Tags: {tags}
        
        Respond with a JSON object containing exactly:
        - "spanish_title": string
        - "spanish_description": string
        - "spanish_tags": string
        
        Return ONLY valid JSON.
        """
        try:
            response = cls._create_chat_completion_with_retry(client, prompt, response_format={"type": "json_object"})
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Translation error: {e}")
            raise

    @classmethod
    def plan_calendar(cls, niche: str, trend_title: str) -> str:
        """Content Calendar Agent: plans optimal publishing dates."""
        if settings.is_openai_mock:
            return "Publish Date: Next Tuesday at 2:00 PM EST. Category: Coding/AI. Pillar: Tutorial Guides."
        
        client = cls.get_client()
        prompt = f"Plan the optimal publishing day, hour, category, and strategic content pillar for a video about: '{trend_title}' in niche '{niche}'."
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Content Calendar error: {e}")
            raise

    @classmethod
    def analytics_feedback(cls, historical_stats: dict) -> str:
        """Analytics Feedback Agent: evaluates past success metrics to improve current script."""
        if settings.is_openai_mock:
            return "Recommendations: Videos with hook questions have +12% early retention. The dark theme background outperformed neon purple by 4% CTR. Apply these details."
        
        client = cls.get_client()
        prompt = f"Based on these historical performance stats: {json.dumps(historical_stats)}, provide 3 specific, actionable recommendations for our next script or thumbnail structure."
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Analytics Feedback error: {e}")
            raise

    @classmethod
    def retrieve_memory(cls, niche: str, db_logs: list[str]) -> str:
        """Memory Agent: retrieves key lessons and warnings from previous logs."""
        if settings.is_openai_mock:
            return "Memory Context: Avoid long introductory greetings; jumps straight to the problem. Keep script hooks under 15 words."
        
        client = cls.get_client()
        logs_text = "\n".join(db_logs[:10])
        prompt = f"Read the history of agent execution logs and outcomes for niche '{niche}'. Extract the top 2 crucial lessons, failures, or constraints to inject into our next generation task:\n\n{logs_text}"
        try:
            response = cls._create_chat_completion_with_retry(client, prompt)
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Memory Agent error: {e}")
            raise

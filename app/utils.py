import atexit
import base64
import datetime
import logging
import os
import textwrap
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from openai import OpenAI

from app import db
from app.models import BlogPost

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None

MAX_BLOG_POSTS = 30
EDITORIAL_START_DATE = datetime.date(2025, 1, 1)
EDITORIAL_TOPICS = [
    {
        "title": "Holistic Wellness Benefits of Saffron for Cardiovascular Support",
        "angle": "Highlight antioxidant and anti-inflammatory effects relevant to Ukraine and the wider EU."
    },
    {
        "title": "Saffron for Mood Support and Stress Relief Backed by Clinical Research",
        "angle": "Cover serotonin pathways, daily dosing guidance, and responsible sourcing from Voloskyi Saffron."
    },
    {
        "title": "Showcase Recipes: Ukrainian and Mediterranean Classics Elevated with Saffron",
        "angle": "Provide step-by-step dishes and pairing tips for home cooks and restaurants."
    },
    {
        "title": "How Saffron Enhances Cognitive Performance and Focus",
        "angle": "Summarise neuroscience findings and practical routines for professionals."
    },
    {
        "title": "Beauty Formulations: Saffron for Radiant Skin and Natural Glow",
        "angle": "Explore cosmeceutical applications, serums, and spa treatments popular in Europe."
    },
    {
        "title": "Crafting Saffron Beverages for Cafés, Bars, and Concept Stores",
        "angle": "Detail signature lattes, lemonades, and mocktails with pricing guidance."
    },
    {
        "title": "Understanding Saffron Grades, ISO Standards, and Quality Assurance",
        "angle": "Explain colouring strength, flavour metrics, and how Voloskyi Saffron is tested."
    },
    {
        "title": "From Field to Jar: The Voloskyi Saffron Supply Story",
        "angle": "Describe cultivation in Ukraine, traceability, and sustainability commitments."
    },
    {
        "title": "Saffron in Integrative and Functional Medicine",
        "angle": "Review clinical trials, dosage forms, and how clinicians incorporate saffron."
    },
    {
        "title": "Pastry Innovation: Desserts and Bakes with Saffron",
        "angle": "Share patisserie ideas, infusion techniques, and flavour balancing."
    },
    {
        "title": "Why Saffron Prices Fluctuate on the European Market",
        "angle": "Analyse harvest yields, logistics, and premium positioning strategies."
    },
    {
        "title": "Strengthening Immunity with Saffron During Seasonal Shifts",
        "angle": "Blend herbalist perspectives with scientific references for European climates."
    },
    {
        "title": "Designing Herbal Tea Blends with Saffron",
        "angle": "Combine botanicals, steeping ratios, and retail packaging inspiration."
    },
    {
        "title": "How Chefs Engineer Menus Around Saffron",
        "angle": "Share costings, plating ideas, and sensory storytelling for diners."
    },
    {
        "title": "Saffron and Mental Wellbeing: Serotonin and Dopamine Insights",
        "angle": "Connect neurochemistry with practical wellness rituals for busy professionals."
    },
    {
        "title": "Home Storage and Brewing Techniques for Premium Saffron",
        "angle": "Provide care tips, bloom methods, and mistakes to avoid."
    },
    {
        "title": "Athletic Recovery and Performance Support with Saffron",
        "angle": "Discuss studies on endurance, inflammation, and supplementation timing."
    },
    {
        "title": "Inside the Lab: Analysing Crocin, Safranal, and Picrocrocin",
        "angle": "Break down chemical markers and how they influence flavour and health."
    },
    {
        "title": "Comparing Saffron Origins: Iran, Spain, Greece, and Ukraine",
        "angle": "Guide buyers on terroir, regulatory landscapes, and flavour profiles."
    },
    {
        "title": "Saffron as a Premium Gift for Corporate and Holiday Occasions",
        "angle": "Offer packaging ideas, messaging, and personalization trends."
    },
    {
        "title": "Plant-Based Cooking Elevated with Saffron",
        "angle": "Show vegan recipes, protein pairings, and nutrition boosts."
    },
    {
        "title": "Taste Science: How Saffron Influences Aroma and Palate",
        "angle": "Explain sensory pathways, pairing matrices, and tasting rituals."
    },
    {
        "title": "Evening Rituals: Saffron for Sleep Hygiene and Relaxation",
        "angle": "Detail teas, diffusers, and mindfulness routines with SEO focus."
    },
    {
        "title": "Mixology Spotlight: Saffron Syrups and Signature Cocktails",
        "angle": "Share bar techniques, ingredient sourcing, and pricing tips."
    },
    {
        "title": "Traditional Medicine Perspectives on Saffron",
        "angle": "Cover Ayurveda, Persian, and European herbal traditions with modern context."
    },
    {
        "title": "Market Outlook: Investing in Saffron and Specialty Spices",
        "angle": "Provide data on demand, export routes, and retail opportunities."
    },
    {
        "title": "Gut Health Synergies with Saffron and Prebiotic Ingredients",
        "angle": "Discuss microbiome research and product formulations."
    },
    {
        "title": "Crafting Saffron-Infused Oils, Butters, and Condiments",
        "angle": "Teach infusion safety, shelf life, and culinary applications."
    },
    {
        "title": "Sustainability and Ethical Sourcing of Saffron",
        "angle": "Highlight fair labour, traceability, and eco packaging."
    },
    {
        "title": "Seasonal Celebrations: Saffron Recipes for European Holidays",
        "angle": "Feature festive menus, cultural insights, and hosting tips."
    },
]

_topic_lines = "\n".join(
    f"{index + 1}. {entry['title']} — {entry['angle']}" for index, entry in enumerate(EDITORIAL_TOPICS)
)

EDITORIAL_SYSTEM_PROMPT = textwrap.dedent(
    f"""
    You are the editorial AI for Voloskyi Saffron, crafting SEO and geo-optimised blog articles for readers across Ukraine and the wider European Union.
    Maintain an evergreen 30-day editorial calendar and loop it indefinitely:
    {_topic_lines}

    Editorial guidelines:
    - Write in English with subtle localisation cues for Central and Eastern Europe.
    - Prioritise health benefits, culinary applications, and premium positioning of saffron grown or curated by Voloskyi Saffron.
    - Include an engaging meta description under 160 characters labelled "Meta Description:" near the top.
    - Produce structured HTML (no <html> or <body> tags). Start with a single <article> element containing one <h1> title, multiple <h2>/<h3> sections, bullet lists, key takeaways, and an FAQ block.
    - Highlight relevant SEO keywords naturally and reference major European markets when appropriate.
    - Finish with a persuasive call-to-action that nudges readers to explore Voloskyi Saffron products or contact the team.
    """
).strip()


def _select_topic(today: datetime.date) -> tuple[int, dict[str, str]]:
    elapsed_days = (today - EDITORIAL_START_DATE).days
    index = elapsed_days % len(EDITORIAL_TOPICS)
    return index, EDITORIAL_TOPICS[index]


def _prune_old_posts(max_posts: int = MAX_BLOG_POSTS) -> None:
    excess_posts = (
        BlogPost.query.order_by(BlogPost.created_at.desc())
        .offset(max_posts)
        .all()
    )
    if not excess_posts:
        return

    for stale_post in excess_posts:
        db.session.delete(stale_post)
    db.session.commit()


def _build_image_prompt(topic: dict[str, str]) -> str:
    return (
        "Elegant editorial photograph illustrating "
        f"{topic['title'].lower()} with premium saffron threads, warm natural light, "
        "fine dining styling, no people, no text, high-resolution."
    )


def _generate_blog_post(app) -> bool:
    with app.app_context():
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("Skipping blog generation; OPENAI_API_KEY missing.")
            return False

        client = OpenAI(api_key=api_key)
        today = datetime.date.today()
        topic_index, topic = _select_topic(today)
        timestamp_label = datetime.datetime.now().strftime("%d %B %Y")
        logger.info("Generating blog post for topic #%s: %s", topic_index + 1, topic["title"])

        try:
            completion = client.responses.create(
                model="gpt-4.1-mini",
                temperature=0.7,
                max_output_tokens=1500,
                input=[
                    {"role": "system", "content": EDITORIAL_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "Produce today's article for the Voloskyi Saffron blog. "
                            f"Focus on topic #{topic_index + 1}: {topic['title']} — {topic['angle']}. "
                            "Incorporate long-tail keywords for premium saffron buyers in Europe, "
                            "mention Ukrainian provenance where relevant, and ensure the article remains evergreen. "
                            "Return only HTML as described."
                        ),
                    },
                ],
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to generate blog post text: %s", exc)
            return False

        content = completion.output_text
        post_title = f"{topic['title']} ({timestamp_label})"
        post = BlogPost(
            title=post_title,
            content=content,
        )

        try:
            image_response = client.images.generate(
                model="gpt-image-1",
                prompt=_build_image_prompt(topic),
                size="1024x1024",
                quality="high",
            )
            image_base64 = image_response.data[0].b64_json
            post.image_data = base64.b64decode(image_base64)
            post.image_mimetype = "image/png"
            post.image_filename = f"blog-{today.isoformat()}-{topic_index + 1}.png"
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("Failed to generate blog image: %s", exc)

        db.session.add(post)
        db.session.commit()
        _prune_old_posts()
        return True


def trigger_blog_post_generation(app) -> bool:
    return _generate_blog_post(app)


def start_scheduler(app) -> None:
    global _scheduler

    if app.config.get("TESTING"):
        return

    if app.config.get("DEBUG") and os.getenv("WERKZEUG_RUN_MAIN") != "true":
        return

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        func=lambda: _generate_blog_post(app),
        trigger="interval",
        days=1,
        id="daily_blog_post",
        replace_existing=True,
    )
    _scheduler.start()
    atexit.register(lambda: _scheduler.shutdown(wait=False))

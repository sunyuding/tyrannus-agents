"""FastMCP server for marketing strategy (Module 3)."""

from mcp.server.fastmcp import FastMCP

from servers.marketing import service

mcp = FastMCP(
    "tyrannus-marketing",
    instructions="Marketing strategy, campaign planning, and content optimization",
)


@mcp.tool()
def analyze_audience(product: str, industry: str) -> str:
    """Analyze target audience for a product or service.

    Args:
        product: The product or service to analyze
        industry: The industry or market vertical
    """
    persona = service.analyze_audience(product, industry)
    return (
        f"Target Audience Analysis\n"
        f"========================\n"
        f"Demographics: {persona.demographics}\n\n"
        f"Pain Points:\n"
        + "\n".join(f"  - {p}" for p in persona.pain_points)
        + f"\n\nPreferred Channels:\n"
        + "\n".join(f"  - {c}" for c in persona.channels)
        + f"\n\nMessaging Strategy:\n{persona.messaging}"
    )


@mcp.tool()
def generate_campaign(
    product: str, goal: str, budget: str, duration: str
) -> str:
    """Generate a marketing campaign plan.

    Args:
        product: Product or service name
        goal: Campaign objective (e.g. awareness, leads, sales)
        budget: Total budget (e.g. "$5000")
        duration: Campaign duration (e.g. "1 month")
    """
    campaign = service.generate_campaign(product, goal, budget, duration)
    return (
        f"Campaign: {campaign.product} (id: {campaign.id})\n"
        f"Goal: {campaign.goal}\n"
        f"Budget: {campaign.budget} | Duration: {campaign.duration}\n\n"
        f"Channels:\n"
        + "\n".join(f"  - {c}" for c in campaign.channels)
        + f"\n\nKPIs:\n"
        + "\n".join(f"  - {k}" for k in campaign.kpis)
        + f"\n\nContent Plan:\n{campaign.content_plan}"
    )


@mcp.tool()
def generate_copy(
    topic: str,
    platform: str,
    tone: str = "professional",
    context: str = "",
) -> str:
    """Generate marketing copy for a specific platform.

    Args:
        topic: The subject of the copy
        platform: Target platform (e.g. facebook, email, landing_page)
        tone: Writing tone — professional, casual, urgent, inspirational
        context: Additional context or brand guidelines
    """
    return service.generate_copy(topic, platform, tone, context)


@mcp.tool()
def generate_schedule(campaign_summary: str, weeks: int = 4) -> str:
    """Generate a content calendar for a campaign.

    Args:
        campaign_summary: Description of the campaign to plan for
        weeks: Number of weeks to plan (default: 4)
    """
    calendar = service.generate_schedule(campaign_summary, weeks)
    lines = ["Content Calendar\n================\n"]
    for week in calendar.weeks:
        lines.append(f"Week {week.week}: {week.theme}")
        for item in week.items:
            lines.append(
                f"  {item.day} | {item.platform} | {item.content_type}: {item.topic}"
            )
            lines.append(f"    {item.description}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
def optimize_content(metrics_summary: str) -> str:
    """Provide optimization suggestions based on content performance metrics.

    Args:
        metrics_summary: Summary of current content performance metrics
            (e.g. engagement rates, reach, conversion data)
    """
    return service.optimize_content(metrics_summary)


def main():
    mcp.run()


if __name__ == "__main__":
    main()

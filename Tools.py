"""Anthropic tool-use schemas + dispatch table."""
import json
from Specter import search_company, enrich_company, SpecterError


TOOL_SCHEMAS = [
    {
        "name": "search_company",
        "description": (
            "Resolve a company name to its primary web domain using Specter's "
            "entity database. Returns the domain string, or null if no match. "
            "Always call this FIRST when given a company name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The company name to look up, e.g. 'Stripe' or 'Monzo Bank'",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "enrich_company",
        "description": (
            "Get the full Specter profile for a company by domain. Returns "
            "operating status, growth stage, funding history, headcount trends, "
            "investor list, highlights, certifications, and recent news. Call "
            "this AFTER search_company has resolved a domain."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "The company's primary domain, e.g. 'stripe.com'",
                },
            },
            "required": ["domain"],
        },
    },
]


def dispatch(tool_name: str, tool_input: dict) -> str:
    """Run a tool and return JSON-serialized result for the model."""
    try:
        if tool_name == "search_company":
            result = search_company(tool_input["name"])
            return json.dumps({"domain": result})
        if tool_name == "enrich_company":
            result = enrich_company(tool_input["domain"])
            return json.dumps(result, default=str)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except SpecterError as e:
        return json.dumps({"error": str(e), "no_match": True})
    except Exception as e:
        return json.dumps({"error": f"Tool error: {e}"})
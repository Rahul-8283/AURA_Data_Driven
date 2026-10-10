import asyncio

from fastapi import APIRouter, HTTPException

from app.services.ga.material import BatteryMaterial
from app.services.retrieval.graph_search import get_material_graph

router = APIRouter()


@router.get("/material/{material_name}")
async def get_material_graph_endpoint(material_name: str):
    """
    Returns a { nodes: [], links: [] } payload describing the chemistry
    knowledge graph for a given material formula (e.g. LiNi0.5Mn0.5O2),
    used by the frontend's react-force-graph-2d visualization.
    """
    try:
        elements = list(BatteryMaterial.parse_string_to_dict(material_name).keys())
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse material formula: {e}")

    graph = await asyncio.to_thread(get_material_graph, material_name, elements)
    return graph

import { useEffect, useState } from 'react';
import ForceGraph2D, { type NodeObject, type LinkObject } from 'react-force-graph-2d';
import api from '../../lib/api';
import type { MaterialGraphNode, MaterialGraphLink, MaterialGraphResponse } from '../../types/research';

type GraphNode = NodeObject<MaterialGraphNode>;
type GraphLink = LinkObject<MaterialGraphNode, MaterialGraphLink>;

const NODE_COLORS: Record<MaterialGraphNode['type'], string> = {
  Material: '#d0b66c',
  Element: '#6ea8d8',
  Property: '#8f9b68',
  DegradationMode: '#d59a72',
};

export default function MaterialGraph({ materialName }: { materialName: string }) {
  const [graphData, setGraphData] = useState<MaterialGraphResponse>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadGraph = async () => {
      setLoading(true);
      setError('');
      try {
        const { data } = await api.get<MaterialGraphResponse>(
          `/api/v1/graph/material/${encodeURIComponent(materialName)}`
        );
        if (isMounted) setGraphData(data);
      } catch {
        if (isMounted) setError('Could not load the chemistry graph for this material.');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    void loadGraph();
    return () => {
      isMounted = false;
    };
  }, [materialName]);

  if (loading) return <div className="material-graph__status">Loading knowledge graph…</div>;
  if (error) return <div className="material-graph__status">{error}</div>;
  if (graphData.nodes.length === 0) {
    return <div className="material-graph__status">No graph data available for this material.</div>;
  }

  return (
    <div className="material-graph">
      <ForceGraph2D<MaterialGraphNode, MaterialGraphLink>
        graphData={graphData}
        nodeId="id"
        height={420}
        backgroundColor="transparent"
        nodeLabel={(node: GraphNode) => `${node.label} (${node.type})`}
        nodeColor={(node: GraphNode) => NODE_COLORS[node.type] ?? '#999999'}
        linkLabel={(link: GraphLink) => link.type}
        linkColor={() => 'rgba(255,255,255,0.25)'}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        nodeCanvasObjectMode={() => 'after'}
        nodeCanvasObject={(node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
          if (node.x === undefined || node.y === undefined) return;
          const fontSize = 11 / globalScale;
          ctx.font = `${fontSize}px Manrope, sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'top';
          ctx.fillStyle = 'rgba(255,255,255,0.75)';
          ctx.fillText(node.label, node.x, node.y + 8);
        }}
      />
      <div className="material-graph__legend">
        <span><i style={{ background: NODE_COLORS.Material }} /> Material</span>
        <span><i style={{ background: NODE_COLORS.Element }} /> Element</span>
        <span><i style={{ background: NODE_COLORS.Property }} /> Property</span>
        <span><i style={{ background: NODE_COLORS.DegradationMode }} /> Degradation Mode</span>
      </div>
    </div>
  );
}

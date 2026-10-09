import Graph from 'graphology';
import forceAtlas2 from 'graphology-layout-forceatlas2';
import Sigma from 'sigma';
import { buildGraph } from '../../../frontend/src/graph-data.js';

// Same layout and renderer settings as frontend/src/graph-viewer.js, so the graph
// looks as it does in the product; edges and labels stay on while the camera moves.
const LAYOUT = { barnesHutOptimize: true, gravity: 1, scalingRatio: 10, slowDown: 5 };
const RENDERER = {
  labelColor: { color: '#f5f1ec' }, labelFont: 'DM Sans, sans-serif', labelSize: 12, labelDensity: .08,
  labelRenderedSizeThreshold: 6, defaultEdgeColor: '#34303f', stagePadding: 70, minCameraRatio: .02, maxCameraRatio: 5,
  hideEdgesOnMove: false, hideLabelsOnMove: false,
};

const frame = () => new Promise(resolve => requestAnimationFrame(resolve));
const easeInOut = t => t < .5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2;

function seeded(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Breadth-first from the most connected node, so the graph grows outward along its edges.
function growthOrder(full) {
  const start = full.nodes().reduce((best, node) => full.degree(node) > full.degree(best) ? node : best);
  const order = [start];
  const seen = new Set(order);
  for (let index = 0; index < order.length; index++) {
    full.forEachNeighbor(order[index], neighbor => { if (!seen.has(neighbor)) { seen.add(neighbor); order.push(neighbor); } });
  }
  full.forEachNode(node => { if (!seen.has(node)) order.push(node); });
  return { start, order };
}

window.play = async (data, { grow = 10000, settle = 2500, zoom = 4500, hold = 3500, ratio = .2 } = {}) => {
  const full = buildGraph(data);
  const graph = new Graph({ multi: true, type: 'directed' });
  const renderer = new Sigma(graph, document.getElementById('graph-canvas'), RENDERER);
  const random = seeded(7);
  const { start, order } = growthOrder(full);

  const add = node => {
    const anchor = full.neighbors(node).find(neighbor => graph.hasNode(neighbor));
    const { x, y } = anchor ? graph.getNodeAttributes(anchor) : { x: 0, y: 0 };
    graph.addNode(node, { ...full.getNodeAttributes(node), x: x + (random() - .5) * 10, y: y + (random() - .5) * 10 });
    full.forEachEdge(node, (edge, attributes, source, target) => {
      if (graph.hasNode(source) && graph.hasNode(target) && !graph.hasEdge(edge)) graph.addEdgeWithKey(edge, source, target, attributes);
    });
  };

  const began = performance.now();
  while (graph.order < order.length) {
    const target = Math.ceil(order.length * easeInOut(Math.min(1, (performance.now() - began) / grow)));
    while (graph.order < Math.max(1, target)) add(order[graph.order]);
    forceAtlas2.assign(graph, { iterations: 2, settings: LAYOUT });
    await frame();
  }
  const settled = performance.now() + settle;
  while (performance.now() < settled) { forceAtlas2.assign(graph, { iterations: 2, settings: LAYOUT }); await frame(); }

  const focus = renderer.getNodeDisplayData(start);
  await renderer.getCamera().animate({ x: focus.x, y: focus.y, ratio }, { duration: zoom, easing: 'cubicInOut' });
  await renderer.getCamera().animate({ ratio: ratio * .8 }, { duration: hold, easing: 'linear' });
  return { nodes: graph.order, edges: graph.size, focus: full.getNodeAttribute(start, 'label') };
};

<template>
  <div class="single-graph-card">
    <div class="graph-card-header">
      <span class="graph-title">{{ title }}</span>
    </div>
    <div class="graph-card-body">
      <svg ref="svgRef" class="graph-svg"></svg>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import * as d3 from 'd3';
import axios from 'axios';

const props = defineProps({
  data: {
    type: Object,
    required: true
  },
  title: {
    type: String,
    default: ''
  },
  pathSource: {
    type: Object,
    default: null
  },
  pathTarget: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['node-select', 'update:pathSource', 'update:pathTarget', 'clear-path']);

const svgRef = ref(null);
let simulation = null;
let d3Zoom = null;
let d3Svg = null;
let nodeSelection = null;
let linkSelection = null;
let width = 0;
let height = 0;
let colorScale = null;
let radiusScale = null;
let linkedByIndex = {};
let currentNodes = [];
let currentLinks = [];
let currentPathNodes = [];

const markerBaseId = computed(() => {
  return props.title.replace(/[^a-zA-Z0-9_-]/g, '-');
});

function renderGraph() {
  if (!svgRef.value || !props.data) return;

  if (simulation) {
    simulation.stop();
  }

  d3.select(svgRef.value).selectAll('*').remove();

  let tooltip = d3.select('body').select('.d3-tooltip');
  if (tooltip.empty()) {
    tooltip = d3.select('body')
      .append('div')
      .attr('class', 'd3-tooltip');
  }

  const nodes = JSON.parse(JSON.stringify(props.data.nodes));
  const links = JSON.parse(JSON.stringify(props.data.links));
  
  currentNodes = nodes;
  currentLinks = links;

  const linkCounts = {};
  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
    const targetId = typeof d.target === 'object' ? d.target.id : d.target;
    linkCounts[`${sourceId},${targetId}`] = true;
  });

  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
    const targetId = typeof d.target === 'object' ? d.target.id : d.target;
    d.isBidirectional = linkCounts[`${targetId},${sourceId}`] === true;
  });

  const container = svgRef.value.parentElement;
  width = container.clientWidth;
  height = container.clientHeight;

  d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height);

  const defs = d3.select(svgRef.value).append('defs');
  
  defs.append('marker')
    .attr('id', `arrowhead-${markerBaseId.value}`)
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 9)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('xoverflow', 'visible')
    .append('svg:path')
    .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
    .attr('fill', '#D2D2D7')
    .style('stroke', 'none');

  defs.append('marker')
    .attr('id', `arrow-highlight-${markerBaseId.value}`)
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 9)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('xoverflow', 'visible')
    .append('svg:path')
    .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
    .attr('fill', '#007AFF')
    .style('stroke', 'none');

  const pageranks = nodes.map(d => d.pagerank || 0);
  const minPR = Math.min(...pageranks);
  const maxPR = Math.max(...pageranks);

  radiusScale = d3.scaleLinear()
    .domain([minPR, maxPR])
    .range([5, 25]);

  colorScale = d3.scaleOrdinal()
    .range(['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']);

  linkedByIndex = {};
  links.forEach(d => {
    const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
    const targetId = typeof d.target === 'object' ? d.target.id : d.target;
    linkedByIndex[`${sourceId},${targetId}`] = true;
    linkedByIndex[`${targetId},${sourceId}`] = true;
  });

  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(80))
    .force('charge', d3.forceManyBody().strength(-250))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collide', d3.forceCollide().radius(d => radiusScale(d.pagerank || 0) + 2));

  d3Zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
    });

  d3Svg = d3.select(svgRef.value);
  d3Svg.call(d3Zoom);
  
  d3Svg.on('click', function(event) {
    if (event.target === this) {
      clearPath();
      emit('clear-path');
    }
  });

  const g = d3.select(svgRef.value).append('g');

  linkSelection = g.append('g')
    .selectAll('path')
    .data(links)
    .enter()
    .append('path')
    .attr('fill', 'none')
    .attr('stroke', '#D2D2D7')
    .attr('opacity', 0.7)
    .attr('stroke-width', 2)
    .attr('marker-end', `url(#arrowhead-${markerBaseId.value})`)
    .on('mouseover', (event, d) => {
      tooltip
        .style('opacity', 1)
        .html(`发送方: ${d.source.id}<br>接收方: ${d.target.id}`);
    })
    .on('mousemove', (event) => {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 28) + 'px');
    })
    .on('mouseout', () => {
      tooltip.style('opacity', 0);
    });

  nodeSelection = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', d => radiusScale(d.pagerank || 0))
    .attr('fill', d => colorScale(d.group || 0))
    .attr('stroke', '#FFFFFF')
    .attr('stroke-width', 2)
    .on('mouseover', (event, d) => {
      tooltip
        .style('opacity', 1)
        .html(`节点: ${d.id}<br>度数: ${d.degree}<br>重要度得分: ${(d.pagerank || 0).toFixed(4)}<br>所属社区群组: Group ${d.group || 0}`);

      if (props.pathSource || props.pathTarget || currentPathNodes.length > 0) return;

      nodeSelection.style('opacity', (o) => {
        return linkedByIndex[`${d.id},${o.id}`] || d.id === o.id ? 1 : 0.1;
      });

      linkSelection
        .style('opacity', (o) => {
          return o.source.id === d.id || o.target.id === d.id ? 1 : 0.1;
        })
        .style('stroke-width', (o) => {
          return o.source.id === d.id || o.target.id === d.id ? 4 : 2;
        });
    })
    .on('mousemove', (event) => {
      tooltip
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY - 28) + 'px');
    })
    .on('mouseout', () => {
      tooltip.style('opacity', 0);

      if (props.pathSource || props.pathTarget || currentPathNodes.length > 0) return;

      nodeSelection.style('opacity', 1);
      linkSelection
        .style('opacity', 0.7)
        .style('stroke-width', 2);
    })
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended))
    .on('dblclick', (event, d) => {
      d.fx = null;
      d.fy = null;
      d3.select(event.currentTarget)
        .attr('stroke', null)
        .attr('stroke-width', null);
      simulation.alpha(1).restart();
      emit('node-select', d);
    })
    .on('contextmenu', handleRightClick);

  g.append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text(d => d.id)
    .attr('font-size', 11)
    .attr('dx', 10)
    .attr('dy', 3);

  function calculateShortenedPath(d) {
    const dx = d.target.x - d.source.x;
    const dy = d.target.y - d.source.y;
    const dr = Math.sqrt(dx * dx + dy * dy);
    
    if (dr === 0) return "";
    
    const nodeStrokeWidth = 3;
    const safetyBuffer = 2;
    const targetR = radiusScale(d.target.pagerank || 0) + nodeStrokeWidth + safetyBuffer;
    
    const targetX = d.target.x - (dx * targetR) / dr;
    const targetY = d.target.y - (dy * targetR) / dr;

    return `M${d.source.x},${d.source.y}L${targetX},${targetY}`;
  }

  simulation.on('tick', () => {
    linkSelection.attr('d', calculateShortenedPath);

    nodeSelection
      .attr('cx', d => d.x)
      .attr('cy', d => d.y);

    g.selectAll('text')
      .attr('x', d => d.x)
      .attr('y', d => d.y);
  });

  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }

  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }

  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = d.x;
    d.fy = d.y;
    d3.select(event.currentTarget)
      .attr('stroke', '#333')
      .attr('stroke-width', 3);
  }

  updatePathHighlight();
}

function handleRightClick(event, d) {
  event.preventDefault();
  
  if (!props.pathSource) {
    emit('update:pathSource', d);
    d3.select(event.currentTarget).attr('stroke', '#007AFF').attr('stroke-width', 4);
    return;
  }
  
  if (props.pathSource && !props.pathTarget) {
    emit('update:pathTarget', d);
    d3.select(event.currentTarget).attr('stroke', '#007AFF').attr('stroke-width', 4);
  }
}

async function updatePathHighlight() {
  if (!props.pathSource || !props.pathTarget) {
    clearPath();
    return;
  }

  const sourceId = props.pathSource.id;
  const targetId = props.pathTarget.id;

  const nodeExists = currentNodes.some(n => n.id === sourceId) && currentNodes.some(n => n.id === targetId);
  
  if (!nodeExists) {
    nodeSelection.style('opacity', 0.2);
    nodeSelection
      .filter(d => d.id === sourceId || d.id === targetId)
      .style('opacity', 1)
      .attr('stroke', '#007AFF')
      .attr('stroke-width', 4);
    linkSelection.style('opacity', 0.1);
    return;
  }

  try {
    const response = await axios.post('http://127.0.0.1:5000/api/shortest-path', {
      source: sourceId,
      target: targetId,
      links: props.data.links
    });
    
    currentPathNodes = response.data.path;
    renderPathAnimation(currentPathNodes);
  } catch (error) {
    nodeSelection.style('opacity', 0.2);
    nodeSelection
      .filter(d => d.id === sourceId || d.id === targetId)
      .style('opacity', 1)
      .attr('stroke', '#007AFF')
      .attr('stroke-width', 4);
    linkSelection.style('opacity', 0.1);
  }
}

function renderPathAnimation(pathArray) {
  function isLinkInPath(link, path) {
    const sId = typeof link.source === 'object' ? link.source.id : link.source;
    const tId = typeof link.target === 'object' ? link.target.id : link.target;
    for (let i = 0; i < path.length - 1; i++) {
      if (path[i] === sId && path[i+1] === tId) {
        return true;
      }
    }
    return false;
  }

  linkSelection
    .style('opacity', d => isLinkInPath(d, pathArray) ? 1 : 0.1)
    .attr('stroke', d => isLinkInPath(d, pathArray) ? '#007AFF' : '#D2D2D7')
    .attr('stroke-width', d => isLinkInPath(d, pathArray) ? 4 : 2)
    .attr('marker-end', d => isLinkInPath(d, pathArray) ? `url(#arrow-highlight-${markerBaseId.value})` : `url(#arrowhead-${markerBaseId.value})`)
    .style('stroke-dasharray', d => isLinkInPath(d, pathArray) ? '10, 10' : 'none')
    .style('animation', d => isLinkInPath(d, pathArray) ? 'dash 1s linear infinite' : 'none');

  nodeSelection.style('opacity', d => pathArray.includes(d.id) ? 1 : 0.1);
  
  nodeSelection
    .filter(d => d.id === props.pathSource?.id || d.id === props.pathTarget?.id)
    .attr('stroke', '#007AFF')
    .attr('stroke-width', 4);
}

function clearPath() {
  currentPathNodes = [];
  
  if (nodeSelection) {
    nodeSelection
      .attr('stroke', '#FFFFFF')
      .attr('stroke-width', 2)
      .style('opacity', 1);
  }
  if (linkSelection) {
    linkSelection
      .style('opacity', 0.7)
      .attr('stroke', '#D2D2D7')
      .attr('stroke-width', 2)
      .attr('marker-end', `url(#arrowhead-${markerBaseId.value})`)
      .style('stroke-dasharray', 'none')
      .style('animation', 'none');
  }
}

watch(() => props.data, () => {
  renderGraph();
}, { deep: false });

watch([() => props.pathSource, () => props.pathTarget], () => {
  updatePathHighlight();
}, { deep: true });

onMounted(() => {
  renderGraph();
});

onUnmounted(() => {
  if (simulation) {
    simulation.stop();
  }
});
</script>

<style scoped>
.single-graph-card {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.graph-card-header {
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.8);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.graph-title {
  font-size: 13px;
  font-weight: 500;
  color: #1D1D1F;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.graph-card-body {
  flex: 1;
  position: relative;
  overflow: hidden;
  background-color: #F5F5F7;
}

.graph-svg {
  width: 100%;
  height: 100%;
}
</style>
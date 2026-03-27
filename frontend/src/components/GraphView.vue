<template>
  <div class="graph-view">
    <svg ref="svgRef" class="graph-svg"></svg>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  graphData: {
    type: Object,
    required: true
  }
})

const svgRef = ref(null)
let simulation = null

function renderGraph() {
  if (!svgRef.value || !props.graphData) return

  // 清理旧的动画
  if (simulation) {
    simulation.stop()
  }

  // 清除旧的画布内容
  d3.select(svgRef.value).selectAll('*').remove()

  // 对传入的数据进行深拷贝，切断响应式关联
  const nodes = JSON.parse(JSON.stringify(props.graphData.nodes))
  const links = JSON.parse(JSON.stringify(props.graphData.links))

  // 获取 SVG 容器的尺寸
  const container = svgRef.value.parentElement
  const width = container.clientWidth
  const height = container.clientHeight

  // 设置 SVG 尺寸
  d3.select(svgRef.value)
    .attr('width', width)
    .attr('height', height)

  // 创建箭头标记
  d3.select(svgRef.value)
    .append('defs')
    .append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '-0 -5 10 10')
    .attr('refX', 20)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('xoverflow', 'visible')
    .append('svg:path')
    .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
    .attr('fill', '#999')
    .style('stroke', 'none')

  // 创建力导向模拟
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2))

  // 创建缩放行为
  const zoom = d3.zoom()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform)
    })

  // 应用缩放行为
  d3.select(svgRef.value)
    .call(zoom)

  // 创建一个包含所有元素的组
  const g = d3.select(svgRef.value)
    .append('g')

  // 绘制边
  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .enter()
    .append('line')
    .attr('stroke', '#999')
    .attr('stroke-opacity', 0.6)
    .attr('marker-end', 'url(#arrowhead)')

  // 绘制节点
  const node = g.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', d => Math.max(5, d.degree * 2)) // 根据度数设置半径
    .attr('fill', '#69b3a2')
    .call(d3.drag()
      .on('start', dragstarted)
      .on('drag', dragged)
      .on('end', dragended)
    )

  // 添加节点标签
  g.append('g')
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text(d => d.id)
    .attr('font-size', 12)
    .attr('dx', 12)
    .attr('dy', 4)

  // 更新力导向模拟
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    g.selectAll('text')
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  })

  // 拖拽开始
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart()
    d.fx = d.x
    d.fy = d.y
  }

  // 拖拽中
  function dragged(event, d) {
    d.fx = event.x
    d.fy = event.y
  }

  // 拖拽结束
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0)
    d.fx = null
    d.fy = null
  }
}

// 当 graphData 变化时重新渲染
watch(
  () => props.graphData,
  () => {
    nextTick(() => {
      renderGraph()
    })
  },
  { deep: false }
)

// 当组件挂载后渲染
onMounted(() => {
  nextTick(() => {
    renderGraph()
  })
})
</script>

<style scoped>
.graph-view {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.graph-svg {
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>

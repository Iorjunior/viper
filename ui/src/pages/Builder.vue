<script setup lang="ts">
  import { ref, onMounted } from 'vue'
  import {
    VueFlow,
    useVueFlow,
    type Node,
    type Edge,
    type Connection,
  } from '@vue-flow/core'
  import { fetchStages } from '../api/stages'
  import type { StageDefinition } from '../api/types'
  import '@vue-flow/core/dist/style.css'
  import '@vue-flow/core/dist/theme-default.css'

  const { addNodes, addEdges, onConnect, removeNodes, getNodes } = useVueFlow()

  const pipelineName = ref('custom-pipeline')
  const availableStages = ref<StageDefinition[]>([])
  const selectedNode = ref<Node | null>(null)
  const isExportModalOpen = ref(false)
  const exportedJson = ref('')

  // Initial default pipeline flow
  const initialNodes: Node[] = [
    {
      id: 'source',
      type: 'default',
      label: 'Download Video (source)',
      position: { x: 50, y: 150 },
      data: {
        stage: 'download_video',
        params: { source: '{{ inputs.source }}' },
      },
      class:
        'p-4 rounded-xl border border-lime-500/40 bg-neutral-900 text-neutral-100 font-semibold text-xs shadow-md',
    },
    {
      id: 'audio',
      type: 'default',
      label: 'Extract Audio (audio)',
      position: { x: 300, y: 150 },
      data: {
        stage: 'extract_audio',
        params: { video: '{{ stages.source.output }}' },
      },
      class:
        'p-4 rounded-xl border border-lime-500/40 bg-neutral-900 text-neutral-100 font-semibold text-xs shadow-md',
    },
    {
      id: 'transcribe',
      type: 'default',
      label: 'Transcribe (transcribe)',
      position: { x: 550, y: 150 },
      data: {
        stage: 'transcribe',
        params: { audio: '{{ stages.audio.output }}' },
      },
      class:
        'p-4 rounded-xl border border-lime-500/40 bg-neutral-900 text-neutral-100 font-semibold text-xs shadow-md',
    },
  ]

  const initialEdges: Edge[] = [
    {
      id: 'e-source-audio',
      source: 'source',
      target: 'audio',
      animated: true,
      style: { stroke: '#84cc16', strokeWidth: 2 },
    },
    {
      id: 'e-audio-transcribe',
      source: 'audio',
      target: 'transcribe',
      animated: true,
      style: { stroke: '#84cc16', strokeWidth: 2 },
    },
  ]

  const nodes = ref<Node[]>(initialNodes)
  const edges = ref<Edge[]>(initialEdges)

  onConnect((params: Connection) => {
    addEdges({
      ...params,
      animated: true,
      style: { stroke: '#84cc16', strokeWidth: 2 },
    })
  })

  async function loadAvailableStages() {
    try {
      availableStages.value = await fetchStages()
    } catch {
      // Fallback default stages if API is offline
      availableStages.value = [
        {
          name: 'download_video',
          description: 'Download remote video from URL',
          inputs: { source: 'string' },
        },
        {
          name: 'extract_audio',
          description: 'Extract audio stream via FFmpeg',
          inputs: { video: 'string' },
        },
        {
          name: 'separate_vocals',
          description: 'Split vocals & background audio',
          inputs: { audio: 'string' },
        },
        {
          name: 'transcribe',
          description: 'Speech to text transcription',
          inputs: { audio: 'string' },
        },
        {
          name: 'translate',
          description: 'Translate transcript to target language',
          inputs: { text: 'string' },
        },
        {
          name: 'synthesize',
          description: 'Text to speech synthesis',
          inputs: { text: 'string' },
        },
        {
          name: 'compose',
          description: 'Remux video with new dubbed audio',
          inputs: { video: 'string', audio: 'string' },
        },
      ]
    }
  }

  onMounted(() => {
    loadAvailableStages()
  })

  function addStageNode(stageDef: StageDefinition) {
    const current = getNodes.value
    const id = `${stageDef.name}_${current.length + 1}`
    const x = 100 + (current.length % 4) * 220
    const y = 80 + Math.floor(current.length / 4) * 120

    addNodes({
      id,
      type: 'default',
      label: `${stageDef.name} (${id})`,
      position: { x, y },
      data: { stage: stageDef.name, params: {} },
      class:
        'p-4 rounded-xl border border-lime-500/40 bg-neutral-900 text-neutral-100 font-semibold text-xs shadow-md',
    })
  }

  function onNodeClick(e: { node: Node }) {
    selectedNode.value = e.node
  }

  function deleteSelectedNode() {
    if (!selectedNode.value) return
    removeNodes(selectedNode.value.id)
    selectedNode.value = null
  }

  function exportPipeline() {
    const currentNodes = getNodes.value
    const stages = currentNodes.map((node) => ({
      id: node.id,
      stage: node.data?.stage || node.id,
      inputs: node.data?.params || {},
    }))

    const manifest = {
      id: pipelineName.value.toLowerCase().replace(/[^a-z0-9_-]/g, '-'),
      name: pipelineName.value,
      description: 'Custom pipeline generated via Viper Visual Builder.',
      icon: 'workflow',
      tags: ['custom', 'builder'],
      builtin: false,
      inputs: {
        source: {
          type: 'string',
          label: 'Source media path or URL',
        },
      },
      stages,
      outputs: {},
    }

    exportedJson.value = JSON.stringify(manifest, null, 2)
    isExportModalOpen.value = true
  }

  function downloadExportedJson() {
    const blob = new Blob([exportedJson.value], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${pipelineName.value}.json`
    a.click()
    URL.revokeObjectURL(url)
  }
</script>

<template>
  <div class="space-y-6">
    <!-- Builder Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
    >
      <div class="flex items-center space-x-3">
        <UInput
          v-model="pipelineName"
          placeholder="Pipeline Name"
          class="w-64 font-bold text-lg"
        />
        <span class="text-xs text-neutral-400 font-mono"
          >Visual DAG Builder</span
        >
      </div>

      <div class="flex items-center space-x-3">
        <UButton
          color="neutral"
          variant="outline"
          icon="i-lucide-download"
          size="sm"
          @click="exportPipeline"
        >
          Export JSON
        </UButton>
      </div>
    </div>

    <!-- Main Workspace -->
    <div
      class="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-170px)] min-h-[600px]"
    >
      <!-- Left: Stage Palette (2-3 cols) -->
      <div
        class="lg:col-span-3 xl:col-span-2 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] p-4 flex flex-col space-y-3 overflow-y-auto"
      >
        <h3
          class="text-xs font-bold uppercase tracking-wider text-neutral-500 mb-1"
        >
          Stage Library
        </h3>
        <p class="text-xs text-neutral-400 mb-2">
          Click to add a stage node to the canvas:
        </p>

        <div
          v-for="st in availableStages"
          :key="st.name"
          class="p-3 rounded-xl border border-[var(--ui-border)] hover:border-lime-500/50 bg-[var(--ui-bg-muted)]/50 cursor-pointer transition-colors space-y-1 group"
          @click="addStageNode(st)"
        >
          <div class="flex items-center justify-between">
            <span
              class="font-bold text-xs text-neutral-200 group-hover:text-lime-400 transition-colors"
            >
              {{ st.name }}
            </span>
            <UIcon
              name="i-lucide-plus"
              class="w-3.5 h-3.5 text-neutral-400 group-hover:text-lime-400"
            />
          </div>
          <p class="text-[11px] text-neutral-500 line-clamp-2 leading-tight">
            {{ st.description || 'Viper processing stage.' }}
          </p>
        </div>
      </div>

      <!-- Center: Flow Canvas (9-10 cols) -->
      <div
        class="lg:col-span-9 xl:col-span-10 rounded-2xl border border-[var(--ui-border)] bg-neutral-950 overflow-hidden relative shadow-inner"
      >
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-viewport="{ zoom: 1, x: 50, y: 50 }"
          class="w-full h-full"
          @node-click="onNodeClick"
        />

        <!-- Node Inspector Mini Overlay -->
        <div
          v-if="selectedNode"
          class="absolute bottom-4 right-4 p-4 rounded-xl border border-neutral-800 bg-neutral-900/95 backdrop-blur text-xs text-neutral-200 space-y-3 w-80 shadow-2xl z-20"
        >
          <div class="flex items-center justify-between">
            <span class="font-bold text-lime-400"
              >Node: {{ selectedNode.id }}</span
            >
            <UButton
              color="error"
              variant="ghost"
              size="xs"
              icon="i-lucide-trash-2"
              @click="deleteSelectedNode"
            >
              Delete
            </UButton>
          </div>
          <div class="space-y-1 text-neutral-400">
            <div>
              Stage:
              <span class="text-neutral-100 font-mono">{{
                selectedNode.data?.stage
              }}</span>
            </div>
            <div>
              Position:
              <span class="font-mono"
                >({{ Math.round(selectedNode.position.x) }},
                {{ Math.round(selectedNode.position.y) }})</span
              >
            </div>
          </div>
          <UButton
            color="neutral"
            variant="outline"
            size="xs"
            class="w-full"
            @click="selectedNode = null"
          >
            Close Inspector
          </UButton>
        </div>
      </div>
    </div>

    <!-- Export JSON Slideover / Modal -->
    <USlideover
      v-model:open="isExportModalOpen"
      title="Export Pipeline Manifest"
      description="Copy or download the pipeline manifest JSON."
    >
      <template #body>
        <div class="space-y-4">
          <pre
            class="p-4 rounded-xl bg-neutral-900 text-lime-400 text-xs font-mono overflow-x-auto max-h-[500px] leading-relaxed"
            >{{ exportedJson }}</pre>
        </div>
      </template>

      <template #footer>
        <div class="flex items-center justify-end space-x-3 w-full">
          <UButton
            color="neutral"
            variant="outline"
            @click="isExportModalOpen = false"
          >
            Close
          </UButton>
          <UButton
            color="primary"
            icon="i-lucide-download"
            @click="downloadExportedJson"
          >
            Download .json
          </UButton>
        </div>
      </template>
    </USlideover>
  </div>
</template>

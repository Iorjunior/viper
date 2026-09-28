<script setup lang="ts">
  import { computed } from 'vue'
  import { getAssetUrl } from '../api/runs'

  const props = defineProps<{
    outputsJson?: string
  }>()

  interface ExtractedMedia {
    type: 'video' | 'audio' | 'subtitle' | 'other'
    path: string
    url: string
    name: string
  }

  const extractedMediaList = computed<ExtractedMedia[]>(() => {
    if (!props.outputsJson) return []

    let data: unknown
    try {
      data = JSON.parse(props.outputsJson)
    } catch {
      return []
    }

    const results: ExtractedMedia[] = []

    function scan(val: unknown) {
      if (!val) return
      if (typeof val === 'string') {
        const lower = val.toLowerCase()
        if (
          lower.endsWith('.mp4') ||
          lower.endsWith('.webm') ||
          lower.endsWith('.mov')
        ) {
          results.push({
            type: 'video',
            path: val,
            url: getAssetUrl(val),
            name: val.split('/').pop() || val,
          })
        } else if (
          lower.endsWith('.mp3') ||
          lower.endsWith('.wav') ||
          lower.endsWith('.ogg') ||
          lower.endsWith('.m4a')
        ) {
          results.push({
            type: 'audio',
            path: val,
            url: getAssetUrl(val),
            name: val.split('/').pop() || val,
          })
        } else if (lower.endsWith('.srt') || lower.endsWith('.vtt')) {
          results.push({
            type: 'subtitle',
            path: val,
            url: getAssetUrl(val),
            name: val.split('/').pop() || val,
          })
        }
      } else if (typeof val === 'object') {
        for (const v of Object.values(val as Record<string, unknown>)) {
          scan(v)
        }
      }
    }

    scan(data)
    // Deduplicate by path
    const seen = new Set<string>()
    return results.filter((item) => {
      if (seen.has(item.path)) return false
      seen.add(item.path)
      return true
    })
  })

  const parsedJsonFormatted = computed(() => {
    if (!props.outputsJson) return '{}'
    try {
      return JSON.stringify(JSON.parse(props.outputsJson), null, 2)
    } catch {
      return props.outputsJson
    }
  })
</script>

<template>
  <div class="space-y-6">
    <!-- Render Media Players -->
    <div v-if="extractedMediaList.length > 0" class="space-y-6">
      <div
        v-for="item in extractedMediaList"
        :key="item.path"
        class="p-5 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] space-y-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <UIcon
              :name="
                item.type === 'video'
                  ? 'i-lucide-video'
                  : item.type === 'audio'
                    ? 'i-lucide-volume-2'
                    : 'i-lucide-file-text'
              "
              class="w-4 h-4 text-lime-500"
            />
            <span class="font-medium text-sm truncate max-w-md">{{
              item.name
            }}</span>
          </div>

          <a
            :href="item.url"
            download
            class="text-xs font-medium text-lime-500 hover:text-lime-400 flex items-center space-x-1"
          >
            <UIcon name="i-lucide-download" class="w-3.5 h-3.5" />
            <span>Download</span>
          </a>
        </div>

        <!-- Video Player -->
        <div
          v-if="item.type === 'video'"
          class="rounded-xl overflow-hidden bg-black/90 aspect-video flex items-center justify-center"
        >
          <video controls class="w-full h-full object-contain" :src="item.url">
            Your browser does not support the video tag.
          </video>
        </div>

        <!-- Audio Player -->
        <div v-else-if="item.type === 'audio'" class="pt-2">
          <audio controls class="w-full" :src="item.url">
            Your browser does not support audio playback.
          </audio>
        </div>

        <!-- Subtitles -->
        <div
          v-else
          class="text-xs text-neutral-400 font-mono p-3 rounded-lg bg-[var(--ui-bg-muted)]"
        >
          Subtitle file generated at {{ item.path }}
        </div>
      </div>
    </div>

    <!-- Raw Output JSON Details -->
    <div
      class="p-5 rounded-2xl border border-[var(--ui-border)] bg-[var(--ui-bg)] space-y-2"
    >
      <div class="flex items-center justify-between">
        <h4
          class="text-xs font-bold uppercase tracking-wider text-neutral-500"
        >
          Raw Outputs Payload
        </h4>
      </div>
      <pre
        class="p-4 rounded-xl bg-neutral-900 text-lime-400 text-xs font-mono overflow-x-auto max-h-80 leading-relaxed"
        >{{ parsedJsonFormatted }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NAlert, NButton, NSpace, NCard, NText, NTag, NDescriptions, NDescriptionsItem } from "naive-ui";

const props = defineProps<{
  event: Record<string, any>;
}>();

const emit = defineEmits<{
  continue: [];
  abort: [];
}>();

const isSmartStop = computed(() => props.event.type === "smart_stop");
const title = computed(() => (isSmartStop.value ? "智能停触发" : "检查点暂停"));
const type = computed(() => (isSmartStop.value ? "warning" : "info"));

const reason = computed(() => props.event.reason || "");
const chapterNumber = computed(() => props.event.chapter_number || "");
const pullScore = computed(() => props.event.pull_score);
const emotionalDebt = computed(() => props.event.emotional_debt);
</script>

<template>
  <NCard :bordered="false" size="small" style="margin-bottom: 16px">
    <NAlert :type="type as any" :title="title" closable>
      <template #default>
        <div v-if="reason" style="margin-bottom: 8px">
          <NText>{{ reason }}</NText>
        </div>
        <NDescriptions v-if="chapterNumber || pullScore" :column="2" size="small" label-placement="left" style="margin-bottom: 8px">
          <NDescriptionsItem v-if="chapterNumber" label="章节">{{ chapterNumber }}</NDescriptionsItem>
          <NDescriptionsItem v-if="pullScore" label="追读力">{{ pullScore }}/10</NDescriptionsItem>
          <NDescriptionsItem v-if="emotionalDebt" label="情感债务">{{ emotionalDebt }}</NDescriptionsItem>
        </NDescriptions>
        <NSpace>
          <NButton type="primary" size="small" @click="emit('continue')">接纳并继续</NButton>
          <NButton size="small" @click="emit('abort')">中止任务</NButton>
        </NSpace>
      </template>
    </NAlert>
  </NCard>
</template>

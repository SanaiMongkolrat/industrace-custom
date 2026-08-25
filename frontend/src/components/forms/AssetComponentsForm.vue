<template>
  <div>
    <div class="flex align-items-center mb-2">
      <span>{{ t('assetComponents.createSectionHint') }}</span>
      <Button class="ml-2 p-button-text p-button-sm" :label="expanded ? t('common.actions.hide') : t('common.actions.show')" icon="pi pi-chevron-down" @click="expanded = !expanded" />
    </div>

    <transition name="fade">
      <div v-if="expanded">
        <DataTable :value="localComponents" responsiveLayout="scroll" class="p-datatable-sm mb-3" :emptyMessage="t('assetComponents.noComponents')">
          <Column field="model_label" :header="t('assetComponents.model')">
            <template #body="{ data }">
              {{ data.model_label || t('assetComponents.selectModel') }}
            </template>
          </Column>
          <Column field="quantity" :header="t('assetComponents.quantity')" />
          <Column field="notes" :header="t('assetComponents.notes')">
            <template #body="{ data }">
              <span class="text-muted">{{ data.notes || '-' }}</span>
            </template>
          </Column>
          <Column v-if="editable" :header="t('common.strings.actions')" style="width:120px">
            <template #body="slotProps">
              <Button icon="pi pi-trash" class="p-button-text p-button-danger p-button-sm" :label="t('assetComponents.removeComponent')" @click="removeComponent(slotProps.index)" />
            </template>
          </Column>
        </DataTable>

        <div v-if="editable" class="p-fluid grid">
          <div class="col-12 md:col-4 p-field">
            <label>{{ t('assetComponents.model') }}*</label>
            <Dropdown
              v-model="draft.model_lifecycle_id"
              :options="modelOptions"
              optionValue="id"
              optionLabel="label"
              :placeholder="t('assetComponents.selectModel')"
              :filter="true"
              class="w-full"
            />
          </div>
          <div class="col-12 md:col-2 p-field">
            <label>{{ t('assetComponents.quantity') }}*</label>
            <InputNumber v-model="draft.quantity" :min="1" class="w-full" />
          </div>
          <div class="col-12 md:col-5 p-field">
            <label>{{ t('assetComponents.notes') }}</label>
            <Textarea v-model="draft.notes" :rows="1" autoResize class="w-full" />
          </div>
          <div class="col-12 md:col-1 p-field flex align-items-end justify-content-center">
            <Button icon="pi pi-plus" :label="t('assetComponents.addComponent')" class="p-button-sm" @click="addComponent" :disabled="!draft.model_lifecycle_id" />
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../../api/api'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'

const props = defineProps({
  components: {
    type: Array,
    default: () => []
  },
  editable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:components'])

const { t } = useI18n()

const localComponents = ref(copyComponents(props.components))
const modelOptions = ref([])
const expanded = ref(false)
const draft = ref(emptyRow())

function emptyRow() {
  return { model_lifecycle_id: null, quantity: 1, notes: '', model_label: '' }
}

function copyComponents(arr) {
  return arr.map(c => ({ ...c }))
}

function emitChange() {
  emit('update:components', copyComponents(localComponents.value))
}

async function fetchModelOptions() {
  try {
    const res = await api.getModelLifecycles({ limit: 500 })
    modelOptions.value = (res.data || []).map(lc => ({
      id: lc.id,
      label: `${lc.manufacturer_name || '?'} - ${lc.model_name}${lc.asset_type_name ? ' (' + lc.asset_type_name + ')' : ''}`
    }))
  } catch (err) {
    // Silently fail — model list will be empty
  }
}

function addComponent() {
  if (!draft.value.model_lifecycle_id) return
  const selected = modelOptions.value.find(m => m.id === draft.value.model_lifecycle_id)
  localComponents.value.push({
    model_lifecycle_id: draft.value.model_lifecycle_id,
    quantity: draft.value.quantity || 1,
    notes: draft.value.notes || '',
    model_label: selected ? selected.label : ''
  })
  draft.value = emptyRow()
  emitChange()
}

function removeComponent(idx) {
  localComponents.value.splice(idx, 1)
  emitChange()
}

watch(() => props.components, (newVal) => {
  localComponents.value = copyComponents(newVal || [])
}, { deep: true })

onMounted(() => {
  fetchModelOptions()
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter, .fade-leave-to {
  opacity: 0;
}
.text-muted {
  color: #6c757d;
  font-style: italic;
}
</style>

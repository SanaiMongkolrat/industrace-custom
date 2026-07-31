<template>
  <form @submit.prevent="handleSubmit">
    <div class="p-fluid">
      <div class="p-field">
        <label for="name">{{ t('common.fields.name') }} <span class="required">*</span></label>
        <InputText id="name" v-model="form.name" required />
      </div>
      <div class="p-field">
        <label for="description">{{ t('common.fields.description') }}</label>
        <InputText id="description" v-model="form.description" />
      </div>
      <div class="p-field">
        <label for="color">{{ t('common.fields.color') }}</label>
        <ColorPicker id="color" v-model="form.color" />
      </div>
      <div class="p-field">
        <label for="order">{{ t('common.fields.order') }}</label>
        <InputNumber id="order" v-model="form.order" :min="0" />
      </div>
      <div class="p-field-checkbox">
        <Checkbox id="active" v-model="form.active" :binary="true" />
        <label for="active">{{ t('common.fields.active') }}</label>
      </div>
      <div class="flex justify-content-end gap-2 mt-4">
        <Button :label="t('common.actions.cancel')" class="p-button-text" @click="emit('cancel')" />
        <Button :label="t('common.actions.save')" type="submit" />
      </div>
    </div>
  </form>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import ColorPicker from 'primevue/colorpicker'

const { t } = useI18n()

const props = defineProps({
  status: { type: Object, default: null }
})

const emit = defineEmits(['submit', 'cancel'])

const form = ref({
  name: '',
  description: '',
  color: '#64748b',
  active: true,
  order: 0
})

watch(() => props.status, (newVal) => {
  if (newVal) {
    form.value = { ...newVal }
  } else {
    form.value = { name: '', description: '', color: '#64748b', active: true, order: 0 }
  }
}, { immediate: true })

function handleSubmit() {
  emit('submit', { ...form.value })
}
</script>

<style scoped>
.required { color: #dc3545; font-weight: bold; }
.p-field { margin-bottom: 1rem; }
.p-field label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
.p-field-checkbox { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; }
</style>

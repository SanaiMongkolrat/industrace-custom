<template>
  <div class="lifecycle-statuses-page">
    <div class="page-header">
      <h1>{{ t('lifecycleStatuses.title') }}</h1>
      <Button 
        v-if="canWrite('lifecycle_statuses')" 
        :label="t('common.actions.create')" 
        icon="pi pi-plus" 
        @click="showDialog = true" 
      />
    </div>
    <DataTable :value="statuses" :loading="loading" paginator :rows="10" :rowsPerPageOptions="[5, 10, 25]">
      <Column field="name" :header="t('common.fields.name')" sortable></Column>
      <Column field="description" :header="t('common.fields.description')"></Column>
      <Column field="color" :header="t('common.fields.color')">
        <template #body="{ data }">
          <span :style="{ background: data.color, color: '#fff', padding: '0.2rem 0.5rem', borderRadius: '4px' }">{{ data.color }}</span>
        </template>
      </Column>
      <Column field="order" :header="t('common.fields.order')" sortable></Column>
      <Column field="active" :header="t('common.fields.active')">
        <template #body="{ data }">
          <i :class="data.active ? 'pi pi-check text-green-500' : 'pi pi-times text-red-500'" />
        </template>
      </Column>
      <Column v-if="canWrite('lifecycle_statuses') || canDelete('lifecycle_statuses')" :header="t('common.strings.actions')">
        <template #body="{ data }">
          <Button 
            v-if="canWrite('lifecycle_statuses')"
            icon="pi pi-pencil" 
            class="p-button-rounded p-button-text p-button-info" 
            @click="editStatus(data)" 
          />
          <Button 
            v-if="canDelete('lifecycle_statuses')"
            icon="pi pi-trash" 
            class="p-button-rounded p-button-text p-button-danger" 
            @click="deleteStatus(data.id)" 
          />
        </template>
      </Column>
    </DataTable>
    <Dialog v-model:visible="showDialog" :header="t('common.actions.create')" :modal="true" :style="{ width: '30vw' }">
      <LifecycleStatusForm @submit="createStatus" @cancel="showDialog = false" />
    </Dialog>
    <Dialog v-model:visible="editDialog" :header="t('common.actions.edit')" :modal="true" :style="{ width: '30vw' }">
      <LifecycleStatusForm :status="editingStatus" @submit="updateStatus" @cancel="onEditCancel" />
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { usePermissions } from '../composables/usePermissions'
import api from '../api/api'
import LifecycleStatusForm from '../components/forms/LifecycleStatusForm.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

const toast = useToast()
const { t } = useI18n()
const { canWrite, canDelete } = usePermissions()

const statuses = ref([])
const loading = ref(false)
const showDialog = ref(false)
const editDialog = ref(false)
const editingStatus = ref(null)

onMounted(() => {
  fetchStatuses()
})

async function fetchStatuses() {
  loading.value = true
  try {
    const response = await api.getLifecycleStatuses()
    statuses.value = response.data
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('lifecycleStatuses.messages.fetchError'), life: 3000 })
  } finally {
    loading.value = false
  }
}

function editStatus(status) {
  editingStatus.value = { ...status }
  nextTick(() => editDialog.value = true)
}

function onEditCancel() {
  editDialog.value = false
  editingStatus.value = null
}

async function createStatus(data) {
  try {
    await api.createLifecycleStatus(data)
    toast.add({ severity: 'success', summary: t('common.messages.success'), detail: t('lifecycleStatuses.messages.created'), life: 3000 })
    showDialog.value = false
    fetchStatuses()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('lifecycleStatuses.messages.createError'), life: 3000 })
  }
}

async function updateStatus(data) {
  try {
    await api.updateLifecycleStatus(editingStatus.value.id, data)
    toast.add({ severity: 'success', summary: t('common.messages.updated'), detail: t('lifecycleStatuses.messages.updated'), life: 3000 })
    editDialog.value = false
    fetchStatuses()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('lifecycleStatuses.messages.updateError'), life: 3000 })
  }
}

async function deleteStatus(id) {
  if (!confirm(t('lifecycleStatuses.deleteConfirm'))) return
  try {
    await api.deleteLifecycleStatus(id)
    toast.add({ severity: 'success', summary: t('common.messages.deleted'), detail: t('lifecycleStatuses.messages.deleted'), life: 3000 })
    fetchStatuses()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('lifecycleStatuses.messages.deleteError'), life: 3000 })
  }
}
</script>

<style scoped>
.lifecycle-statuses-page {
  padding: 1rem;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
</style>

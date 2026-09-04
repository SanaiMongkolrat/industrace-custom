<template>
  <div class="assettypes-page">
    <div class="page-header">
      <h1>{{ t('assettypes.title') }}</h1>
      <Button 
        v-if="canWrite('asset_types')" 
        :label="t('common.actions.create')" 
        icon="pi pi-plus" 
        @click="showDialog = true" 
      />
    </div>

    <DataTable 
      :value="assettypes" 
      :loading="loading" 
      paginator 
      :rows="10" 
      :rowsPerPageOptions="[5, 10, 25]"
    >
      <Column field="name" :header="t('common.fields.name')" sortable></Column>
      <Column field="description" :header="t('common.fields.description')"></Column>
      <Column field="purdue_level" :header="t('assettypes.fields.purdueLevel')">
        <template #body="{ data }">
          <span v-if="data.purdue_level !== null && data.purdue_level !== undefined">
            {{ t('assettypes.level' + (data.purdue_level === 1.5 ? '1_5' : data.purdue_level)) }}
          </span>
          <span v-else>-</span>
        </template>
      </Column>
      <Column field="useful_life_years" :header="t('assettypes.fields.usefulLifeYearsShort')" sortable>
        <template #body="{ data }">
          <span v-if="data.useful_life_years !== null && data.useful_life_years !== undefined">
            {{ data.useful_life_years }}
          </span>
          <span v-else class="p-text-secondary">-</span>
        </template>
      </Column>
      <Column field="useful_life_inheritance_enabled" :header="t('assettypes.fields.inherit')">
        <template #body="{ data }">
          <i v-if="data.useful_life_inheritance_enabled" class="pi pi-check" :title="t('assettypes.strings.inheritanceOn')"></i>
          <i v-else class="pi pi-times" :title="t('assettypes.strings.inheritanceOff')"></i>
        </template>
      </Column>
      <Column v-if="canWrite('asset_types') || canDelete('asset_types')" :header="t('common.strings.actions')">
        <template #body="{ data }">
          <Button 
            v-if="canWrite('asset_types')"
            icon="pi pi-pencil" 
            class="p-button-rounded p-button-text p-button-info" 
            @click="editAssetType(data)" 
          />
          <Button 
            v-if="canDelete('asset_types')"
            icon="pi pi-trash" 
            class="p-button-rounded p-button-text p-button-danger" 
            @click="deleteAssetType(data.id)" 
          />
        </template>
      </Column>
    </DataTable>

    <Dialog 
      v-model:visible="showDialog" 
      :header="t('common.actions.create')" 
      :modal="true" 
      :style="{ width: '40vw' }"
    >
      <AssetTypeForm 
        :tenantId="tenantId" 
        @submit="createAssetType" 
        @cancel="showDialog = false" 
      />
    </Dialog>

    <Dialog 
      v-model:visible="editDialog" 
      :header="t('common.actions.edit')" 
      :modal="true" 
      :style="{ width: '40vw' }"
    >
      <AssetTypeForm 
        :tenantId="tenantId" 
        :assettype="editingAssetType" 
        @submit="updateAssetType" 
        @cancel="onEditCancel" 
      />
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { usePermissions } from '../composables/usePermissions'
import api from '../api/api'

import AssetTypeForm from '../components/forms/AssetTypeForm.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

const toast = useToast()
const router = useRouter()
const { t } = useI18n()
const { canWrite, canDelete } = usePermissions()

const assettypes = ref([])
const loading = ref(false)
const showDialog = ref(false)
const editDialog = ref(false)
const editingAssetType = ref(null)

const tenantId = ref('...') 

onMounted(() => {
  fetchAssetTypes()
})

async function fetchAssetTypes() {
  loading.value = true
  try {
    const response = await api.getAssetTypes()
    assettypes.value = response.data
  } catch (error) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assettypes.messages.fetchError'), life: 3000 })
  } finally {
    loading.value = false
  }
}

function editAssetType(assettype) {
  editingAssetType.value = { ...assettype }
  nextTick(() => editDialog.value = true)
}

function onEditCancel() {
  editDialog.value = false
  editingAssetType.value = null
}

async function createAssetType(data) {
  try {
    await api.createAssetType(data)
    toast.add({ severity: 'success', summary: t('common.messages.success'), detail: t('assettypes.messages.created'), life: 3000 })
    showDialog.value = false
    fetchAssetTypes()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('assettypes.messages.createError'), life: 3000 })
  }
}

async function updateAssetType(data) {
  try {
    await api.updateAssetType(editingAssetType.value.id, data)
    toast.add({ severity: 'success', summary: t('common.messages.updated'), detail: t('assetTypes.messages.updated'), life: 3000 })
    editDialog.value = false
    fetchAssetTypes()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.updateError'), detail: t('assetTypes.messages.updateError'), life: 3000 })
  }
}

async function deleteAssetType(id) {
  if (!confirm(t('assetTypes.deleteConfirm'))) return
  try {
    await api.deleteAssetType(id)
    toast.add({ severity: 'success', summary: t('common.messages.deleted'), detail: t('assetTypes.messages.deleted'), life: 3000 })
    fetchAssetTypes()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.deleteError'), detail: t('assetTypes.messages.deleteError'), life: 3000 })
  }
}

</script>

<style scoped>
.assettypes-page {
  padding: 1rem;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
</style>

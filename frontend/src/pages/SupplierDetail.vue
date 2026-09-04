<!--
  - SupplierDetail.vue
  - Componente per la visualizzazione dei dettagli di un fornitore
  - Utilizza i componenti PrimeVue per la gestione del form
-->
<template>
  <div class="p-4">
    <Button icon="pi pi-arrow-left" :label="t('common.actions.back')" class="mb-3" @click="goBack" />
    <h2 class="text-xl mb-4">{{ t('suppliers.title') }}</h2>
    
    <div class="mb-4">
      <h3 class="text-lg font-semibold">{{ t('common.strings.info') }}</h3>
      <p><strong>{{ t('common.fields.name') }}:</strong> {{ supplier.name }}</p>
      <p><strong>{{ t('common.fields.description') }}:</strong> {{ supplier.description }}</p>
      <p><strong>{{ t('suppliers.fields.vatNumber') }}:</strong> {{ supplier.vat_number || '-' }}</p>
      <p><strong>{{ t('suppliers.fields.taxCode') }}:</strong> {{ supplier.tax_code || '-' }}</p>
      <p><strong>{{ t('suppliers.fields.address') }}:</strong> {{ supplier.address || '-' }}</p>
      <p><strong>{{ t('common.fields.city') }}:</strong> {{ supplier.city || '-' }}</p>
      <p><strong>{{ t('common.fields.zipCode') }}:</strong> {{ supplier.zip_code || '-' }}</p>
      <p><strong>{{ t('common.fields.state') }}:</strong> {{ supplier.province || '-' }}</p>
      <p><strong>{{ t('common.fields.country') }}:</strong> {{ supplier.country || '-' }}</p>
      <p><strong>{{ t('common.fields.phone') }}:</strong> {{ supplier.phone || '-' }}</p>
      <p><strong>{{ t('common.fields.email') }}:</strong> {{ supplier.email || '-' }}</p>
      <p><strong>{{ t('common.fields.website') }}:</strong> <a v-if="supplier.website" :href="supplier.website" target="_blank">{{ supplier.website }}</a><span v-else>-</span></p>
      <p><strong>{{ t('common.fields.notes') }}:</strong> {{ supplier.notes || '-' }}</p>
    </div>

    <!-- Sezione Contatti associati -->
    <div class="mb-4">
      <h3 class="text-lg font-semibold">{{ t('contacts.title') }}</h3>
      <div v-if="canWrite('suppliers')" class="flex align-items-center gap-2 mb-2">
        <MultiSelect v-model="selectedContactIds" :options="allContacts" optionLabel="fullName" optionValue="id" :placeholder="t('common.actions.add')" display="chip" class="mr-2" style="min-width:250px" />
        <Button :label="t('common.actions.save')" icon="pi pi-check" class="p-button-sm" @click="updateSupplierContacts" />
        <Button :label="t('common.actions.create')" icon="pi pi-plus" class="p-button-sm" @click="showContactDialog = true" />
      </div>
              <DataTable :value="supplierContacts" :loading="loadingContacts" :emptyMessage="t('contacts.messages.noContacts')">
        <Column field="fullName" :header="t('contacts.fields.fullName')" />
        <Column field="email" :header="t('common.fields.email')" />
        <Column field="phone" :header="t('common.fields.phone')" />
        <Column field="type" :header="t('common.fields.type')" />
        <Column v-if="canWrite('suppliers')" :header="t('common.strings.actions')">
          <template #body="{ data }">
            <Button icon="pi pi-trash" class="p-button-rounded p-button-text p-button-danger" @click="removeContact(data.id)" :title="t('common.actions.remove')" />
          </template>
        </Column>
      </DataTable>
      <Dialog v-model:visible="showContactDialog" :header="t('common.actions.create')" :modal="true" :style="{ width: '30vw' }">
        <ContactForm @submit="createContact" @cancel="showContactDialog = false" />
      </Dialog>
    </div>

    <div>
      <h3 class="text-lg font-semibold mb-2">{{ t('documents.title') }}</h3>
      <FileUpload
        v-if="canWrite('suppliers')"
        name="file"
        :url="`/api/suppliers/${supplier.id}/documents`"
        @upload="fetchDocuments"
        :auto="true"
        :customUpload="false"
        :chooseLabel="t('common.actions.upload')"
      />

      <DataTable :value="documents" class="mt-4" tableStyle="min-width: 100%">
        <Column field="filename" :header="t('common.fields.filename')" />
        <Column field="uploaded_at" :header="t('common.fields.uploadedAt')" />
        <Column :header="t('common.strings.actions')">
          <template #body="{ data }">
            <a :href="data.url" target="_blank" class="p-button p-button-text">{{ t('common.actions.download') }}</a>
            <Button v-if="canWrite('suppliers')" icon="pi pi-trash" class="p-button-text p-button-danger" @click="deleteDocument(data.id)" />
          </template>
        </Column>
      </DataTable>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { usePermissions } from '../composables/usePermissions'
import api from '../api/api'
import { useI18n } from 'vue-i18n'

import FileUpload from 'primevue/fileupload'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import MultiSelect from 'primevue/multiselect'
import Dialog from 'primevue/dialog'
import ContactForm from '../components/forms/ContactForm.vue'

const { t } = useI18n()
const { canWrite } = usePermissions()
const toast = useToast()

const route = useRoute()
const router = useRouter()
const supplierId = route.params.id

const supplier = ref({})
const documents = ref([])

const supplierContacts = ref([])
const allContacts = ref([])
const selectedContactIds = ref([])
const loadingContacts = ref(false)
const showContactDialog = ref(false)

async function fetchSupplier() {
  const res = await api.getSupplier(`${supplierId}`)
  supplier.value = res.data
}

async function fetchDocuments() {
  const res = await api.get(`/api/suppliers/${supplierId}/documents`)
  documents.value = res.data
}

async function fetchAllContacts() {
  try {
    const response = await api.getContacts()
    allContacts.value = response.data.map(mapContact)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('contacts.messages.fetchError'), life: 3000 })
  }
}

async function fetchSupplierContacts() {
  loadingContacts.value = true
  try {
    const response = await api.getSupplierContacts(supplierId)
    supplierContacts.value = response.data.map(mapContact)
    selectedContactIds.value = supplierContacts.value.map(c => c.id)
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('suppliers.messages.fetchContactsError'), life: 3000 })
  } finally {
    loadingContacts.value = false
  }
}

async function updateSupplierContacts() {
  try {
    await api.updateSupplierContacts(supplierId, selectedContactIds.value)
    toast.add({ severity: 'success', summary: t('common.messages.success'), detail: t('suppliers.messages.contactsUpdated'), life: 3000 })
    await fetchSupplierContacts()
  } catch (err) {
    toast.add({ severity: 'error', summary: t('common.messages.error'), detail: t('suppliers.messages.updateContactsError'), life: 3000 })
  }
}

async function removeContact(contactId) {
  await api.deleteSupplierContact(supplierId, contactId)
  await fetchSupplierContacts()
  selectedContactIds.value = supplierContacts.value.map(c => c.id)
}

async function createContact(contactData) {
  await api.createContact(contactData)
  showContactDialog.value = false
  await fetchAllContacts()
  await fetchSupplierContacts()
}

function mapContact(contact) {
  return { ...contact, fullName: `${contact.first_name} ${contact.last_name}` }
}

async function deleteDocument(docId) {
  await api.delete(`/api/documents/${docId}`)
  await fetchDocuments()
}

function goBack() {
  router.push({ name: 'Suppliers' })
}

onMounted(async () => {
  await fetchSupplier()
  await fetchAllContacts()
  await fetchSupplierContacts()
  await fetchDocuments()
})
</script>

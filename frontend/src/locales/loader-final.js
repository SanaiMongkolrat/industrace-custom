import { createI18n } from 'vue-i18n'

// Import delle traduzioni comuni
import itCommon from './it/common.json'
import enCommon from './en/common.json'
import itMenu from './it/menu.json'
import enMenu from './en/menu.json'

// Import delle traduzioni per sezione
import itDashboard from './it/dashboard.json'
import enDashboard from './en/dashboard.json'
import itAssets from './it/assets.json'
import enAssets from './en/assets.json'
import itAssetTypes from './it/assettypes.json'
import enAssetTypes from './en/assettypes.json'
import itAssetStatuses from './it/assetstatuses.json'
import enAssetStatuses from './en/assetstatuses.json'
import itContacts from './it/contacts.json'
import enContacts from './en/contacts.json'
import itFooter from './it/footer.json'
import enFooter from './en/footer.json'
import itLogin from './it/login.json'
import enLogin from './en/login.json'
import itManufacturers from './it/manufacturers.json'
import enManufacturers from './en/manufacturers.json'
import itSuppliers from './it/suppliers.json'
import enSuppliers from './en/suppliers.json'
import itSites from './it/sites.json'
import enSites from './en/sites.json'
import itAreas from './it/areas.json'
import enAreas from './en/areas.json'
import itLocations from './it/locations.json'
import enLocations from './en/locations.json'
import itPcap from './it/pcap.json'
import enPcap from './en/pcap.json'
import itSetup from './it/setup.json'
import enSetup from './en/setup.json'
import itAuditlog from './it/auditlog.json'
import enAuditlog from './en/auditlog.json'
import itProfile from './it/profile.json'
import enProfile from './en/profile.json'
import itNetworkmap from './it/networkMap.json'
import enNetworkmap from './en/networkMap.json'
import itPrint from './it/print.json'
import enPrint from './en/print.json'
import itRoles from './it/roles.json'
import enRoles from './en/roles.json'
import itUsers from './it/users.json'
import enUsers from './en/users.json'
import itGlobalsearch from './it/globalsearch.json'
import enGlobalsearch from './en/globalsearch.json'
import itAssetReviews from './it/assetReviews.json'
import enAssetReviews from './en/assetReviews.json'
import itNotifications from './it/notifications.json'
import enNotifications from './en/notifications.json'
import itISA62443 from './it/isa62443.json'
import enISA62443 from './en/isa62443.json'
import itAssetDependencies from './it/assetDependencies.json'
import enAssetDependencies from './en/assetDependencies.json'
import itVulnerabilities from './it/vulnerabilities.json'
import enVulnerabilities from './en/vulnerabilities.json'
import itSSO from './it/sso.json'
import enSSO from './en/sso.json'
import itMfa from './it/mfa.json'
import enMfa from './en/mfa.json'
import itNetworkProbes from './it/networkProbes.json'
import enNetworkProbes from './en/networkProbes.json'
import itDiscoveredDevices from './it/discoveredDevices.json'
import enDiscoveredDevices from './en/discoveredDevices.json'
import itCore from './it/core.json'
import enCore from './en/core.json'
import itModelLifecycles from './it/modelLifecycles.json'
import enModelLifecycles from './en/modelLifecycles.json'
import itAssetComponents from './it/assetComponents.json'
import enAssetComponents from './en/assetComponents.json'
import itAssetConnections from './it/assetConnections.json'
import enAssetConnections from './en/assetConnections.json'
import itAssetCommunications from './it/assetCommunications.json'
import enAssetCommunications from './en/assetCommunications.json'
import itAssetStatusesNew from './it/assetStatuses.json'
import enAssetStatusesNew from './en/assetStatuses.json'
import itAssetTypesNew from './it/assetTypes.json'
import enAssetTypesNew from './en/assetTypes.json'
import itAssetDetail from './it/assetDetail.json'
import enAssetDetail from './en/assetDetail.json'
import itAssetImport from './it/assetImport.json'
import enAssetImport from './en/assetImport.json'
import itAssetSuppliersTab from './it/assetSuppliersTab.json'
import enAssetSuppliersTab from './en/assetSuppliersTab.json'
import itDocuments from './it/documents.json'
import enDocuments from './en/documents.json'
import itFloorplan from './it/floorplanWithMarkers.json'
import enFloorplan from './en/floorplanWithMarkers.json'
import itForm from './it/form.json'
import enForm from './en/form.json'
import itManufacturerImport from './it/manufacturerImport.json'
import enManufacturerImport from './en/manufacturerImport.json'
import itSupplierImport from './it/supplierImport.json'
import enSupplierImport from './en/supplierImport.json'
import itLifecycleStatuses from './it/lifecycleStatuses.json'
import enLifecycleStatuses from './en/lifecycleStatuses.json'

// Funzione per appiattire gli oggetti annidati
const flattenObject = (obj, prefix = '') => {
  const flattened = {}
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      const newKey = prefix ? `${prefix}.${key}` : key
      if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
        Object.assign(flattened, flattenObject(obj[key], newKey))
      } else {
        flattened[newKey] = obj[key]
      }
    }
  }
  return flattened
}

// Funzione per rilevare la lingua dell'utente
const getUserLanguage = () => {
  // Always return English
  return 'en'
}

// Appiattisci tutte le traduzioni
const messages = {
  it: flattenObject({
    common: itCommon,
    dashboard: itDashboard,
    assets: itAssets,
    assettypes: itAssetTypes,
    assetstatuses: itAssetStatuses,
    contacts: itContacts,
    footer: itFooter,
    menu: itMenu,
    login: itLogin,
    manufacturers: itManufacturers,
    suppliers: itSuppliers,
    sites: itSites,
    areas: itAreas,
    locations: itLocations,
    pcap: itPcap,
    setup: itSetup,
    auditlog: itAuditlog,
    profile: itProfile,
    networkmap: itNetworkmap,
    print: itPrint,
    roles: itRoles,
    users: itUsers,
    globalsearch: itGlobalsearch,
    assetReviews: itAssetReviews,
    notifications: itNotifications,
    isa62443: itISA62443,
    assetDependencies: itAssetDependencies,
    vulnerabilities: itVulnerabilities,
    sso: itSSO,
    mfa: itMfa,
    networkProbes: itNetworkProbes,
    discoveredDevices: itDiscoveredDevices,
    core: itCore,
    modelLifecycles: itModelLifecycles,
    assetComponents: itAssetComponents,
    assetConnections: itAssetConnections,
    assetCommunications: itAssetCommunications,
    assetStatuses: itAssetStatusesNew,
    assetTypes: itAssetTypesNew,
    assetDetail: itAssetDetail,
    assetImport: itAssetImport,
    assetSuppliersTab: itAssetSuppliersTab,
    documents: itDocuments,
    floorplanWithMarkers: itFloorplan,
    form: itForm,
    manufacturerImport: itManufacturerImport,
    supplierImport: itSupplierImport,
    lifecycleStatuses: itLifecycleStatuses
  }),
  en: flattenObject({
    common: enCommon,
    dashboard: enDashboard,
    assets: enAssets,
    assettypes: enAssetTypes,
    assetstatuses: enAssetStatuses,
    contacts: enContacts,
    footer: enFooter,
    menu: enMenu,
    login: enLogin,
    manufacturers: enManufacturers,
    suppliers: enSuppliers,
    sites: enSites,
    areas: enAreas,
    locations: enLocations,
    pcap: enPcap,
    setup: enSetup,
    auditlog: enAuditlog,
    profile: enProfile,
    networkmap: enNetworkmap,
    print: enPrint,
    roles: enRoles,
    users: enUsers,
    globalsearch: enGlobalsearch,
    assetReviews: enAssetReviews,
    notifications: enNotifications,
    isa62443: enISA62443,
    assetDependencies: enAssetDependencies,
    vulnerabilities: enVulnerabilities,
    sso: enSSO,
    mfa: enMfa,
    networkProbes: enNetworkProbes,
    discoveredDevices: enDiscoveredDevices,
    core: enCore,
    modelLifecycles: enModelLifecycles,
    assetComponents: enAssetComponents,
    assetConnections: enAssetConnections,
    assetCommunications: enAssetCommunications,
    assetStatuses: enAssetStatusesNew,
    assetTypes: enAssetTypesNew,
    assetDetail: enAssetDetail,
    assetImport: enAssetImport,
    assetSuppliersTab: enAssetSuppliersTab,
    documents: enDocuments,
    floorplanWithMarkers: enFloorplan,
    form: enForm,
    manufacturerImport: enManufacturerImport,
    supplierImport: enSupplierImport,
    lifecycleStatuses: enLifecycleStatuses
  })
}

// Configurazione i18n
const i18n = createI18n({
  locale: getUserLanguage(),
  fallbackLocale: 'en',
  messages,
  flatJson: true,
  legacy: false,
  globalInjection: true,
  silentTranslationWarn: false,
  silentFallbackWarn: false,
  missingWarn: true,
  fallbackWarn: true
})

// Funzione per cambiare lingua
export function setLanguage(locale) {
  if (locale === 'it' || locale === 'en') {
    i18n.global.locale.value = locale
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('user-lang', locale)
    }
    return true
  }
  return false
}

export default i18n

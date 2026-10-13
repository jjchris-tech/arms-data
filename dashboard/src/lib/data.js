const BASE = import.meta.env.BASE_URL + 'data/'
const cache = new Map()

function load(path) {
  if (!cache.has(path)) {
    cache.set(path, fetch(BASE + path).then(res => {
      if (!res.ok) throw new Error(`Could not load ${path} (${res.status})`)
      return res.json()
    }).catch(err => {
      cache.delete(path)
      throw err
    }))
  }
  return cache.get(path)
}

export const loadIndex = () => load('countries.json')
export const loadCountry = iso3 => load(`country/${iso3}.json`)
export const loadValidation = () => load('validation.json')
export const loadSuppliers = () => load('suppliers.json')
export const loadSupplier = iso3 => load(`supplier/${iso3}.json`)
export const loadUnVotes = () => load('research/un_votes.json')
export const loadManifest = () => load('downloads/manifest.json')
export const downloadUrl = file => BASE + 'downloads/' + file

import data from "./api-data.json" with { type: "json" }

const MAX_BODY_BYTES = 1048576
const AMOUNT_RE = /^\d{1,18}(?:\.\d{1,6})?$/
const CURRENCY_RE = /^[A-Z]{3}$/
const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/

function jsonResponse(status, payload) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  })
}

class DataError extends Error {}

function requireText(value, label) {
  if (typeof value !== "string" || !value.trim()) {
    throw new DataError(`${label}: a nonempty string is required`)
  }
  return value.trim()
}

function parseAmount(value, label, { zero = false } = {}) {
  if (typeof value !== "string") {
    throw new DataError(`${label}: use a decimal string`)
  }
  if (!AMOUNT_RE.test(value)) {
    throw new DataError(`${label}: use up to 18 digits and 6 decimal places, without separators`)
  }
  const [whole, frac = ""] = value.split(".")
  const intVal = BigInt(whole + frac)
  if (intVal < 0n || (!zero && intVal === 0n)) {
    throw new DataError(`${label}: invalid amount`)
  }
  return { value: intVal, scale: frac.length }
}

function multiplyDecimal(a, b) {
  return { value: a.value * b.value, scale: a.scale + b.scale }
}

function addDecimals(items) {
  const maxScale = items.reduce((max, item) => Math.max(max, item.scale), 0)
  const total = items.reduce((sum, item) => {
    const factor = 10n ** BigInt(maxScale - item.scale)
    return sum + item.value * factor
  }, 0n)
  return { value: total, scale: maxScale }
}

function compareDecimal(a, b) {
  const maxScale = Math.max(a.scale, b.scale)
  const left = a.value * 10n ** BigInt(maxScale - a.scale)
  const right = b.value * 10n ** BigInt(maxScale - b.scale)
  return left < right ? -1 : left > right ? 1 : 0
}

function formatDecimal({ value, scale }) {
  const digits = value.toString()
  if (scale === 0) return digits
  const padded = digits.padStart(scale + 1, "0")
  const splitIdx = padded.length - scale
  return `${padded.slice(0, splitIdx)}.${padded.slice(splitIdx)}`
}

function quoteTotal(payload) {
  const quantity = parseAmount(payload.quantity, "quantity")
  const price = parseAmount(payload.unit_price, "unit_price", { zero: true })
  const costs = {}
  const missing = []
  for (const key of ["freight", "tax", "other_costs"]) {
    const raw = payload[key]
    if (raw === undefined || raw === null) {
      costs[key] = null
      missing.push(key)
    } else {
      costs[key] = parseAmount(raw, key, { zero: true })
    }
  }
  const subtotal = multiplyDecimal(quantity, price)
  const total = missing.length > 0 ? null : formatDecimal(addDecimals([subtotal, costs.freight, costs.tax, costs.other_costs]))
  return {
    subtotal: formatDecimal(subtotal),
    total,
    missing,
  }
}

function parseTimestamp(value, label) {
  const raw = requireText(value, label)
  if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(raw)) {
    throw new DataError(`${label}: timezone required`)
  }
  const ms = Date.parse(raw)
  if (Number.isNaN(ms)) {
    throw new DataError(`${label}: expected ISO timestamp with timezone`)
  }
  return ms
}

function parseDay(value, label) {
  const raw = requireText(value, label)
  if (!ISO_DATE_RE.test(raw)) {
    throw new DataError(`${label}: expected YYYY-MM-DD`)
  }
  const [y, m, d] = raw.split("-").map(Number)
  const dt = new Date(Date.UTC(y, m - 1, d))
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) {
    throw new DataError(`${label}: expected YYYY-MM-DD`)
  }
  return raw
}

function formatDateInZone(ms, timeZone) {
  try {
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(new Date(ms))
    const byType = Object.fromEntries(parts.map((p) => [p.type, p.value]))
    return `${byType.year}-${byType.month}-${byType.day}`
  } catch {
    throw new DataError(
      "Use a valid destination zone, such as Asia/Kolkata or Europe/London. Install tzdata if the timezone database is missing.",
    )
  }
}

function indexed(rows, name) {
  if (!Array.isArray(rows) || rows.length === 0) {
    throw new DataError(`${name}: nonempty list required`)
  }
  const map = new Map()
  for (const row of rows) {
    if (!row || typeof row !== "object" || Array.isArray(row)) {
      throw new DataError(`${name}: each entry must be an object`)
    }
    const id = requireText(row.id, `${name}.id`)
    if (map.has(id)) {
      throw new DataError(`${name}: duplicate ID`)
    }
    map.set(id, row)
  }
  return map
}

function brandReview(request, quote) {
  const policy = request.brand_policy ?? "exact"
  if (policy !== "exact" && policy !== "alternatives") {
    throw new DataError("brand_policy must be exact or alternatives")
  }
  const missing = []
  const mismatches = []
  const details = {}
  const pairs = [
    ["Brand", "required_brand", "offered_brand"],
    ["Model/part number", "required_model", "offered_model"],
  ]
  for (const [label, requiredKey, offeredKey] of pairs) {
    const required = request[requiredKey] != null ? requireText(request[requiredKey], requiredKey) : null
    const offered = quote[offeredKey] != null ? requireText(quote[offeredKey], offeredKey) : null
    details[requiredKey] = required
    details[offeredKey] = offered
    if (required === null) continue
    if (offered === null) {
      missing.push(`${label} not stated in quotation`)
    } else if (
      required.toLowerCase().trim().split(/\s+/).join(" ") !==
      offered.toLowerCase().trim().split(/\s+/).join(" ")
    ) {
      mismatches.push(`${label} differs from requested value`)
    }
  }
  const constrained = details.required_brand !== null || details.required_model !== null
  let status = constrained ? "matched" : "not_requested"
  const reasons = [...missing, ...mismatches]
  if (missing.length > 0) {
    status = "missing_information"
  } else if (mismatches.length > 0) {
    status = policy === "alternatives" ? "alternative_pending_review" : "mismatch"
    if (policy === "alternatives") {
      reasons.push("Alternative requires buyer review; excluded from eligible ranking")
    }
  }
  return { ...details, policy, status, reasons }
}

function evaluateBundle(bundle, asOfDate = new Date(), demo = false) {
  const asOfMs = asOfDate.getTime()
  if (!bundle || typeof bundle !== "object" || Array.isArray(bundle) || bundle.schema_version !== "1.0") {
    throw new DataError("Expected a version 1.0 bundle object")
  }
  const sources = indexed(bundle.sources, "sources")
  const products = indexed(bundle.products, "products")
  const suppliers = indexed(bundle.suppliers, "suppliers")
  const quotes = indexed(bundle.quotes, "quotes")
  const reqObj = bundle.request
  if (!reqObj || typeof reqObj !== "object" || Array.isArray(reqObj)) {
    throw new DataError("request must be an object")
  }

  for (const source of sources.values()) {
    if (demo && source.data_kind !== "synthetic") {
      throw new DataError("Demo mode requires exclusively synthetic sources")
    }
    if (!demo && (source.data_kind !== "real" || source.permission_confirmed !== true)) {
      throw new DataError("Sources must be declared real and authorized for this use")
    }
    requireText(source.reference, "source.reference")
    requireText(source.reviewed_by, "source.reviewed_by")
    if (parseTimestamp(source.reviewed_at, "source.reviewed_at") > asOfMs) {
      throw new DataError("Source review cannot be in the future")
    }
  }

  const checkProvenance = (row, label) => {
    const sourceId = requireText(row.source_id, `${label}.source_id`)
    if (!sources.has(sourceId)) {
      throw new DataError(`${label}: unknown source`)
    }
    requireText(row.source_record_id, `${label}.source_record_id`)
  }

  for (const product of products.values()) {
    checkProvenance(product, "product")
    requireText(product.name, "product.name")
    requireText(product.specification, "product.specification")
    requireText(product.unit, "product.unit")
  }
  for (const supplier of suppliers.values()) {
    checkProvenance(supplier, "supplier")
    requireText(supplier.name, "supplier.name")
    requireText(supplier.country, "supplier.country")
  }

  const productId = requireText(reqObj.product_id, "request.product_id")
  if (!products.has(productId)) {
    throw new DataError("Request product is not in the catalog")
  }
  const currency = requireText(reqObj.currency, "request.currency")
  if (!CURRENCY_RE.test(currency)) {
    throw new DataError("Currency must be a three-letter uppercase code; verify it with the source")
  }
  const legacyZone = !("decision_timezone" in reqObj) && currency === "INR"
  const zoneName = legacyZone ? "Asia/Kolkata" : requireText(reqObj.decision_timezone, "request.decision_timezone")
  const decisionDayLocal = formatDateInZone(asOfMs, zoneName)
  const unit = requireText(reqObj.unit, "request.unit")
  if (unit !== products.get(productId).unit) {
    throw new DataError("Request unit must match the catalog; no implicit conversions")
  }
  const destination = requireText(reqObj.destination_id, "request.destination_id")
  const quantity = parseAmount(reqObj.quantity, "request.quantity")
  const budget = parseAmount(reqObj.total_budget, "request.total_budget")
  const needed = parseDay(reqObj.needed_by, "request.needed_by")
  if (needed < decisionDayLocal) {
    throw new DataError("Requested delivery deadline is in the past")
  }
  const country = reqObj.supplier_country != null ? requireText(reqObj.supplier_country, "request.supplier_country") : null

  const rows = []
  const seenSourceRecords = new Set()
  for (const [quoteId, quote] of quotes.entries()) {
    checkProvenance(quote, "quote")
    const identity = `${quote.source_id}\u0000${quote.source_record_id}`
    if (seenSourceRecords.has(identity)) {
      throw new DataError("Duplicate quote source record; resolve revisions before comparing")
    }
    seenSourceRecords.add(identity)
    const supplierId = requireText(quote.supplier_id, "quote.supplier_id")
    const quotedProduct = requireText(quote.product_id, "quote.product_id")
    if (!suppliers.has(supplierId) || !products.has(quotedProduct)) {
      throw new DataError("Quote refers to an unknown supplier or product")
    }
    const issued = parseTimestamp(quote.issued_at, "quote.issued_at")
    const received = parseTimestamp(quote.received_at, "quote.received_at")
    const expires = parseTimestamp(quote.valid_until, "quote.valid_until")
    const reviewed = parseTimestamp(quote.reviewed_at, "quote.reviewed_at")
    requireText(quote.reviewed_by, "quote.reviewed_by")
    if (!(issued <= received && received <= reviewed) || expires < issued) {
      throw new DataError("Quote timestamps are inconsistent")
    }
    const total = parseAmount(quote.total_amount, "quote.total_amount")
    const offeredQuantity = parseAmount(quote.quantity, "quote.quantity")
    const quotedCurrency = requireText(quote.currency, "quote.currency")
    if (!CURRENCY_RE.test(quotedCurrency)) {
      throw new DataError("Quote currency must be a three-letter uppercase code")
    }
    const quotedUnit = requireText(quote.unit, "quote.unit")
    const quotedDestination = requireText(quote.destination_id, "quote.destination_id")
    requireText(quote.terms_reference, "quote.terms_reference")
    const promised = parseDay(quote.promised_delivery_date, "quote.promised_delivery_date")
    const issuedLocalDate = formatDateInZone(issued, zoneName)
    if (promised < issuedLocalDate) {
      throw new DataError("Quote delivery date precedes issue date")
    }

    const brand = brandReview(reqObj, quote)
    const reasons = [...brand.reasons]
    if (issued > asOfMs || received > asOfMs || reviewed > asOfMs) {
      reasons.push("Quote or review not available at decision time")
    }
    if (expires <= asOfMs) {
      reasons.push("Quote expired")
    }
    if (quotedProduct !== productId) {
      reasons.push("Different product ID")
    }
    if (quote.specification_confirmed !== true) {
      reasons.push("Exact specifications not confirmed")
    }
    if (quotedUnit !== unit) {
      reasons.push("Different purchasing unit; conversion not verified")
    }
    if (compareDecimal(offeredQuantity, quantity) !== 0) {
      reasons.push("Quote must cover the exact requested quantity; obtain a revised quote")
    }
    if (quotedCurrency !== currency) {
      reasons.push("Different currency; no exchange-rate conversion applied")
    }
    if (quotedDestination !== destination) {
      reasons.push("Different delivery destination")
    }
    if (quote.all_costs_included !== true) {
      reasons.push("Complete taxes, freight and applicable duties not confirmed")
    }
    if (country && suppliers.get(supplierId).country.toLowerCase() !== country.toLowerCase()) {
      reasons.push("Supplier country does not match")
    }
    if (promised > needed) {
      reasons.push("Delivery commitment misses requested deadline")
    }
    if (promised < decisionDayLocal) {
      reasons.push("Delivery commitment is in the past; obtain a revised quote")
    }
    if (quotedCurrency === currency && compareDecimal(total, budget) > 0) {
      reasons.push("Total exceeds budget")
    }

    rows.push({
      quote_id: quoteId,
      supplier_id: supplierId,
      eligible: reasons.length === 0,
      reasons,
      currency: quotedCurrency,
      quoted_total: formatDecimal(total),
      cost_rank: null,
      risk_estimate: null,
      brand_review: brand,
      _totalObj: total,
    })
  }

  const eligible = rows
    .filter((row) => row.eligible)
    .sort((a, b) => compareDecimal(a._totalObj, b._totalObj) || a.quote_id.localeCompare(b.quote_id))

  let previous = null
  let rank = null
  eligible.forEach((row, index) => {
    if (!previous || compareDecimal(row._totalObj, previous) !== 0) {
      rank = index + 1
    }
    row.cost_rank = rank
    previous = row._totalObj
  })

  for (const row of rows) {
    delete row._totalObj
  }

  return {
    schema_version: "1.0",
    decision_at: asOfDate.toISOString(),
    status: demo ? "SYNTHETIC_DEMONSTRATION" : "QUOTATION_REVIEW_ONLY",
    purchase_authorized: false,
    risk_status: "Unavailable: real delivery history has not been validated",
    provenance_status: demo
      ? "Fictional suppliers and quotations for demonstration only"
      : "Operator declarations; authenticity not independently verified",
    ranking_basis: "Lowest documented total among eligible quotes; not overall supplier quality",
    currency,
    decision_timezone: zoneName,
    timezone_basis: legacyZone ? "Legacy India input: Asia/Kolkata" : "Explicit destination timezone",
    eligible_quotes: eligible.length,
    quotes: rows,
  }
}

function buildDemoBundle(now = new Date()) {
  const stamp = (days) => new Date(now.getTime() + days * 86400000).toISOString()
  const dayStr = (days) => stamp(days).slice(0, 10)
  const source = {
    id: "demo",
    data_kind: "synthetic",
    source_type: "synthetic",
    reference: "Generated fictional demonstration; no supplier document",
    reviewed_by: "demo generator",
    reviewed_at: stamp(-1),
  }
  const product = {
    id: "chair",
    source_id: "demo",
    source_record_id: "product",
    name: "Office chair",
    specification: "Adjustable height, fabric seat, five-star base",
    unit: "each",
  }
  const specs = [
    ["10000.00", 5, 3, true],
    ["9000.00", 4, -1, true],
    ["9500.00", 6, 3, false],
  ]
  const suppliers = []
  const quotes = []
  specs.forEach(([total, delivery, expiry, complete], idx) => {
    const num = idx + 1
    const supplierId = `demo-${num}`
    suppliers.push({
      id: supplierId,
      source_id: "demo",
      source_record_id: supplierId,
      name: `Fictional Supplier ${num}`,
      country: "India",
    })
    quotes.push({
      id: `quote-${num}`,
      supplier_id: supplierId,
      source_id: "demo",
      source_record_id: `quote-${num}`,
      product_id: "chair",
      currency: "INR",
      unit: "each",
      quantity: "10",
      total_amount: total,
      destination_id: "Demo office",
      issued_at: stamp(-3),
      received_at: stamp(-2),
      reviewed_at: stamp(-1),
      reviewed_by: "demo generator",
      valid_until: stamp(expiry),
      promised_delivery_date: dayStr(delivery),
      specification_confirmed: true,
      all_costs_included: complete,
      terms_reference: "Fictional terms for teaching only",
    })
  })
  return {
    schema_version: "1.0",
    sources: [source],
    products: [product],
    suppliers,
    quotes,
    request: {
      product_id: "chair",
      currency: "INR",
      unit: "each",
      quantity: "10",
      total_budget: "12000",
      needed_by: dayStr(7),
      destination_id: "Demo office",
      supplier_country: null,
      decision_timezone: "Asia/Kolkata",
    },
  }
}

function gradeConfirmed(row, product, grade) {
  if (!product || !grade) return false
  const p = product.endsWith("s") && product.length > 3 ? product.slice(0, -1) : product
  for (const entry of row.evidence || []) {
    const title = String(entry?.title || "")
    const desc = String(entry?.description || "")
    const text = `${title} ${desc}`.toLowerCase()
    if (text.includes(`no ${p}`) || text.includes(`without ${p}`)) continue
    if (text.includes(p) && text.includes(grade)) return true
  }
  return false
}

function filterSuppliers(rows, query = "", product = "", grade = "", match = "", source = "", country = "") {
  const q = query.trim().toLowerCase()
  const prod = product.trim().toLowerCase()
  const gr = grade.trim().toLowerCase()
  const src = source.trim().toLowerCase()
  const ctry = country.trim().toLowerCase()

  const matches = []
  for (const row of rows) {
    if (src && String(row.source_type || "").toLowerCase() !== src) continue
    if (ctry && String(row.country || "").toLowerCase() !== ctry) continue
    if (q) {
      const parts = [String(row.name || ""), String(row.country || ""), String(row.category || "")]
      for (const item of row.evidence || []) {
        parts.push(String(item?.title || ""))
        parts.push(String(item?.description || ""))
      }
      if (!parts.join(" ").toLowerCase().includes(q)) continue
    }
    if (match === "confirmed" && !gradeConfirmed(row, prod, gr)) continue
    if (match === "unconfirmed" && gradeConfirmed(row, prod, gr)) continue
    matches.push(row)
  }

  if (prod) {
    const p = prod.endsWith("s") && prod.length > 3 ? prod.slice(0, -1) : prod
    const scoreOf = (row) => {
      const confirmed = Boolean(gr && gradeConfirmed(row, prod, gr))
      const hasProd = (row.evidence || []).some((e) =>
        `${e?.title || ""} ${e?.description || ""}`.toLowerCase().includes(p),
      )
      const isSim = row.source_type === "simulated"
      return [confirmed ? 0 : hasProd ? 1 : 2, isSim ? 0 : 1]
    }
    matches.sort((a, b) => {
      const sa = scoreOf(a)
      const sb = scoreOf(b)
      return sa[0] - sb[0] || sa[1] - sb[1]
    })
  }

  return matches
}

function catalogWords(value) {
  const plain = String(value || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
  return new Set(plain.match(/[\p{L}\p{N}_]+/gu) || [])
}

function searchCatalog(records, query, limit = 50) {
  const tokens = catalogWords(query)
  if (tokens.size === 0) return []
  const results = []
  for (const record of records) {
    const source = record.source_record || {}
    const fields = ["codigoItem", "nomeGrupo", "nomeClasse", "nomePdm", "descricaoItem"]
    let text = fields.map((k) => String(source[k] ?? "")).join(" ")
    text += ` ${record.english_title || ""} ${record.english_description || ""}`
    const docWords = catalogWords(text)
    let matchedCount = 0
    for (const token of tokens) {
      if (docWords.has(token)) matchedCount += 1
    }
    if (matchedCount > 0) {
      results.push({
        score: matchedCount / tokens.size,
        code: String(source.codigoItem ?? ""),
        record,
      })
    }
  }
  results.sort((a, b) => b.score - a.score || (a.code < b.code ? -1 : a.code > b.code ? 1 : 0))
  return results.slice(0, limit)
}

const supplierRows = data.suppliers || []
const catalogRows = data.catalog || []
const indexedSuppliers = new Map(supplierRows.map((row) => [row.id, row]))

export default async function handler(req) {
  const url = new URL(req.url)
  const pathname = url.pathname

  if (req.method === "GET") {
    if (pathname === "/api/health") {
      return jsonResponse(200, { status: "ok" })
    }
    if (pathname === "/api/suppliers") {
      const q = url.searchParams.get("q") ?? ""
      const product = url.searchParams.get("product") ?? ""
      const grade = url.searchParams.get("grade") ?? ""
      const match = (url.searchParams.get("match") ?? "").trim()
      const source = (url.searchParams.get("source") ?? "").trim()
      const country = (url.searchParams.get("country") ?? "").trim()

      if (!["", "confirmed", "unconfirmed"].includes(match)) {
        return jsonResponse(400, { error: "match must be confirmed or unconfirmed" })
      }
      if (match && !(product.trim() && grade.trim())) {
        return jsonResponse(400, { error: "match requires product and grade" })
      }
      if (!["", "public", "simulated"].includes(source)) {
        return jsonResponse(400, { error: "source must be public or simulated" })
      }

      const rawOffset = url.searchParams.get("offset") ?? "0"
      const rawLimit = url.searchParams.get("limit") ?? "50"
      const offset = Number(rawOffset)
      const limit = Number(rawLimit)
      if (!Number.isInteger(offset) || !Number.isInteger(limit) || offset < 0 || limit < 1 || limit > 100) {
        return jsonResponse(400, { error: "Expected offset >= 0 and limit 1 to 100" })
      }

      const matches = filterSuppliers(supplierRows, q, product, grade, match, source, country)
      return jsonResponse(200, {
        total: matches.length,
        suppliers: matches.slice(offset, offset + limit),
      })
    }
    if (pathname === "/api/catalog") {
      const q = url.searchParams.get("q") ?? ""
      const items = searchCatalog(catalogRows, q, 50)
      return jsonResponse(200, { items })
    }
    if (pathname === "/api/compare") {
      const ids = [...new Set(url.searchParams.getAll("id"))]
      if (ids.length < 2 || ids.length > 5 || ids.some((id) => !indexedSuppliers.has(id))) {
        return jsonResponse(400, { error: "Supply 2 to 5 distinct known id parameters" })
      }
      return jsonResponse(200, {
        suppliers: ids.map((id) => indexedSuppliers.get(id)),
      })
    }
    if (pathname === "/api/quotes/demo") {
      const now = new Date()
      return jsonResponse(200, evaluateBundle(buildDemoBundle(now), now, true))
    }
    return jsonResponse(404, { error: "Unknown route" })
  }

  if (req.method === "POST") {
    if (pathname !== "/api/quotes/review" && pathname !== "/api/quotes/total") {
      return jsonResponse(404, { error: "Unknown route" })
    }
    try {
      const raw = await req.text()
      const byteLength = new TextEncoder().encode(raw).length
      if (byteLength === 0 || byteLength > MAX_BODY_BYTES) {
        return jsonResponse(400, { error: "Expected JSON body up to 1 MiB" })
      }
      const bundle = JSON.parse(raw)
      if (!bundle || typeof bundle !== "object" || Array.isArray(bundle)) {
        throw new DataError("Expected a quotation bundle object")
      }
      const report = pathname.endsWith("/total")
        ? quoteTotal(bundle)
        : evaluateBundle(bundle, new Date(), false)
      return jsonResponse(200, report)
    } catch (err) {
      return jsonResponse(400, { error: err instanceof Error ? err.message : String(err) })
    }
  }

  return jsonResponse(404, { error: "Unknown route" })
}

export const config = {
  path: "/api/*",
}

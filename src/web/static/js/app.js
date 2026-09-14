/*
  Offline Agri-Input Shop ERP - Client Application Logic
  Secured with 256-Bit Cryptographic Session Tokens & RBAC
*/

// Authentication State
let currentUser = null;

// Global Fetch Interceptor to inject Authorization Bearer Token
const _originalFetch = window.fetch;
window.fetch = async function(url, options = {}) {
    const token = localStorage.getItem("krushidhan_auth_token");
    const opt = options || {};
    const headers = { ...(opt.headers || {}) };

    if (token && typeof url === "string" && url.startsWith("/api/")) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    try {
        const res = await _originalFetch(url, { ...opt, headers });
        if (res.status === 401 && typeof url === "string" && !url.includes("/api/auth/login")) {
            console.warn("Unauthorized API call, redirecting to login portal:", url);
            showLoginOverlay("सत्र संपले आहे. कृपया पुन्हा लॉगिन करा (Session expired, please login again)");
        }
        return res;
    } catch (err) {
        console.error("Network or API Fetch error:", err);
        throw err;
    }
};

// Global State
let currentCart = [];
let allProducts = [];
let allCustomers = [];
let allSuppliers = [];
let allLookups = {};
let farmerStatusList = [];
let isOnlyCreditFilter = false;
let activeFarmerId = null;

let pnlAllProducts = [];

document.addEventListener("DOMContentLoaded", async () => {
    initTabs();
    initKeyboardShortcuts();
    initDefaultDates();
    
    // Authenticate & Verify Session before loading sensitive ERP records
    const isAuthed = await checkAuthState();
    if (isAuthed) {
        await bootstrapDashboard();
    }
});

async function bootstrapDashboard() {
    await loadInitialLookups();
    await initPosBilling();
    loadInventory();
    loadDayBook();
    if (currentUser && currentUser.role === "ADMIN") {
        loadProfitAndLoss();
        loadAuthUsers();
    }
    loadSettings();
    loadFarmerStatusList();
    loadMasterTables();
}


function initDefaultDates() {
    const today = new Date().toISOString().split("T")[0];
    const firstDayMonth = today.substring(0, 8) + "01";
    
    const pnlFrom = document.getElementById("pnl-from-date");
    const pnlTo = document.getElementById("pnl-to-date");
    if (pnlFrom && !pnlFrom.value) pnlFrom.value = firstDayMonth;
    if (pnlTo && !pnlTo.value) pnlTo.value = today;
}

// ----------------- Tab Navigation -----------------
function initTabs() {
    const tabs = document.querySelectorAll(".nav-tab");
    tabs.forEach(tab => {
        tab.addEventListener("click", () => {
            tabs.forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

            tab.classList.add("active");
            const targetId = tab.getAttribute("data-tab");
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.add("active");

            // Auto-refresh relevant tab data
            if (targetId === "tab-farmer-status") loadFarmerStatusList();
            if (targetId === "tab-inventory") loadInventory();
            if (targetId === "tab-accounts") loadDayBook();
            if (targetId === "tab-pnl") loadProfitAndLoss();
            if (targetId === "tab-gst") loadGSTR1();
            if (targetId === "tab-masters") loadMasterTables();
        });
    });
}

// ----------------- Keyboard Shortcuts -----------------
function initKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
        if (e.key === "F2") {
            e.preventDefault();
            resetPosCart();
        } else if (e.ctrlKey && e.key.toLowerCase() === "p") {
            e.preventDefault();
            submitSalesBill();
        }
    });
}

// ----------------- Data Loading -----------------
async function loadInitialLookups() {
    try {
        const res = await fetch("/api/masters/all");
        allLookups = await res.json();
        
        // Populate Categories in master forms and filters
        const catSelects = ["pos-prod-cat", "inv-filter-cat", "m-prod-cat", "m-prod-filter-cat"];
        catSelects.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                const defaultLabel = (id === "m-prod-cat") ? "Select Category" : "All Categories";
                el.innerHTML = `<option value="">${defaultLabel}</option>` + 
                    allLookups.categories.map(c => `<option value="${c.category_id}">${c.category_name}</option>`).join("");
            }
        });

        // Populate Manufacturers in product master
        const mfgSelect = document.getElementById("m-prod-mfg");
        if (mfgSelect && allLookups.manufacturers) {
            mfgSelect.innerHTML = '<option value="">Select Manufacturer</option>' + 
                allLookups.manufacturers.map(m => `<option value="${m.manufacturer_id}">${m.manufacturer_name}</option>`).join("");
        }

        // Populate Units in product master
        const unitSelect = document.getElementById("m-prod-unit");
        if (unitSelect && allLookups.units) {
            unitSelect.innerHTML = allLookups.units.map(u => `<option value="${u.unit_id}">${u.unit_name} (${u.symbol})</option>`).join("");
        }

        // Populate Tax Groups in product master
        const taxSelect = document.getElementById("m-prod-tax");
        if (taxSelect && allLookups.tax_groups) {
            taxSelect.innerHTML = allLookups.tax_groups.map(t => 
                `<option value="${t.tax_group_id}">${t.tax_group_name || 'GST'}</option>`
            ).join("");
        }

        // Load Products & Customers for dropdowns
        await refreshProductList();
        await refreshCustomerList();
        await refreshSupplierList();
    } catch (err) {
        console.error("Failed to load lookups:", err);
    }
}

async function refreshProductList() {
    const res = await fetch("/api/masters/products");
    allProducts = await res.json();
    populateProductDropdown("pos-item-product", allProducts);
    populateProductDropdown("pur-item-product", allProducts);
}

async function refreshCustomerList() {
    const res = await fetch("/api/masters/customers");
    allCustomers = await res.json();
    
    // Populate datalist for POS autocomplete
    const datalist = document.getElementById("pos-customer-datalist");
    if (datalist) {
        datalist.innerHTML = allCustomers.map(c => 
            `<option value="${c.customer_name}">${c.village ? c.village + ' - ' : ''}${c.mobile ? c.mobile + ' - ' : ''}₹${c.current_balance} Due</option>`
        ).join("");
    }

    // Populate accounts receipt dropdown
    const accCustSelect = document.getElementById("acc-receipt-cust");
    if (accCustSelect) {
        accCustSelect.innerHTML = '<option value="">Select Farmer / Customer</option>' + 
            allCustomers.map(c => `<option value="${c.customer_id}">${c.customer_name} (${c.village||'Local'}) - ₹${c.current_balance} Due</option>`).join("");
    }
}

async function refreshSupplierList() {
    const res = await fetch("/api/masters/suppliers");
    allSuppliers = await res.json();
    const suppSelect = document.getElementById("pur-supplier");
    if (suppSelect) {
        suppSelect.innerHTML = '<option value="">Select Supplier</option>' + 
            allSuppliers.map(s => `<option value="${s.supplier_id}">${s.supplier_name} (${s.city||''})</option>`).join("");
    }
    const accSuppSelect = document.getElementById("acc-pay-supp");
    if (accSuppSelect) {
        accSuppSelect.innerHTML = suppSelect.innerHTML;
    }
}

function populateProductDropdown(elementId, products) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = '<option value="">Select Product...</option>' + 
        products.map(p => `<option value="${p.product_id}" data-rate="${p.default_sale_rate}" data-mrp="${p.default_mrp}" data-hsn="${p.hsn_code||''}" data-cgst="${p.cgst_rate||0}" data-sgst="${p.sgst_rate||0}" data-igst="${p.igst_rate||0}" data-unit="${p.unit_symbol||''}">${p.product_name} (Stock: ${p.total_stock} ${p.unit_symbol||''})</option>`).join("");
}

// ----------------- POS Billing Tab -----------------
async function initPosBilling() {
    // Set today's date
    const dateInput = document.getElementById("pos-date");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];

    await fetchNextInvoiceNo();

    // Event listener for product change -> fetch FEFO batches
    const prodSelect = document.getElementById("pos-item-product");
    if (prodSelect) {
        prodSelect.addEventListener("change", async () => {
            const prodId = prodSelect.value;
            if (!prodId) return;
            const selectedOpt = prodSelect.options[prodSelect.selectedIndex];
            document.getElementById("pos-item-rate").value = selectedOpt.getAttribute("data-rate") || "0";
            
            // Fetch batches
            const res = await fetch(`/api/inventory/batches/${prodId}`);
            const batches = await res.json();
            const batchSelect = document.getElementById("pos-item-batch");
            if (batches.length === 0) {
                batchSelect.innerHTML = '<option value="">NO ACTIVE STOCK</option>';
            } else {
                batchSelect.innerHTML = batches.map((b, i) => 
                    `<option value="${b.batch_id}" data-qty="${b.current_qty}" data-rate="${b.sale_rate}" data-mrp="${b.mrp}" data-exp="${b.exp_date||''}" data-batchno="${b.batch_no}">${i === 0 ? '⭐ [FEFO] ' : ''}${b.batch_no} (Exp: ${b.exp_date||'N/A'}) - Qty: ${b.current_qty}</option>`
                ).join("");
            }
        });
    }

    // Auto-detect typed farmer name and auto-fill mobile / village
    const custInput = document.getElementById("pos-cust-name");
    if (custInput) {
        custInput.addEventListener("input", (e) => {
            const typedName = e.target.value.trim().toLowerCase();
            const matched = allCustomers.find(c => c.customer_name.toLowerCase() === typedName);
            if (matched) {
                document.getElementById("pos-cust-mobile").value = matched.mobile || "";
                document.getElementById("pos-cust-village").value = matched.village || "";
            }
        });
    }
}

async function fetchNextInvoiceNo() {
    try {
        const res = await fetch("/api/sales/next-invoice-no");
        const data = await res.json();
        document.getElementById("pos-inv-no").value = data.next_invoice_no;
    } catch (err) {
        console.error(err);
    }
}

function addPosItem() {
    const prodSelect = document.getElementById("pos-item-product");
    const batchSelect = document.getElementById("pos-item-batch");
    const qtyInput = document.getElementById("pos-item-qty");
    const rateInput = document.getElementById("pos-item-rate");
    const discInput = document.getElementById("pos-item-disc");

    const prodId = parseInt(prodSelect.value);
    const batchId = parseInt(batchSelect.value);
    const qty = parseFloat(qtyInput.value);
    const rate = parseFloat(rateInput.value);
    const disc = parseFloat(discInput.value) || 0;

    if (!prodId || isNaN(qty) || qty <= 0 || !batchId) {
        alert("Please select a product, a valid batch, and quantity greater than 0.");
        return;
    }

    const prodOpt = prodSelect.options[prodSelect.selectedIndex];
    const batchOpt = batchSelect.options[batchSelect.selectedIndex];
    const availQty = parseFloat(batchOpt.getAttribute("data-qty"));

    if (qty > availQty) {
        alert(`Insufficient stock in this batch! Available: ${availQty}, Requested: ${qty}`);
        return;
    }

    const cgst = parseFloat(prodOpt.getAttribute("data-cgst")) || 0;
    const sgst = parseFloat(prodOpt.getAttribute("data-sgst")) || 0;
    const igst = parseFloat(prodOpt.getAttribute("data-igst")) || 0;

    // Calculate tax breakdown
    const gross = qty * rate;
    const discAmt = gross * (disc / 100.0);
    const netTaxable = (gross - discAmt) / (1 + ((cgst + sgst + igst) / 100.0));
    const cgstAmt = netTaxable * (cgst / 100.0);
    const sgstAmt = netTaxable * (sgst / 100.0);
    const igstAmt = netTaxable * (igst / 100.0);
    const totalLine = gross - discAmt;

    const item = {
        product_id: prodId,
        product_name: prodOpt.text.split(" (Stock:")[0],
        batch_id: batchId,
        batch_no: batchOpt.getAttribute("data-batchno"),
        exp_date: batchOpt.getAttribute("data-exp"),
        hsn_code: prodOpt.getAttribute("data-hsn"),
        unit_name: prodOpt.getAttribute("data-unit"),
        qty: qty,
        sale_rate: rate,
        mrp: parseFloat(batchOpt.getAttribute("data-mrp")) || rate,
        discount_percent: disc,
        discount_amount: Math.round(discAmt * 100) / 100,
        taxable_amount: Math.round(netTaxable * 100) / 100,
        cgst_rate: cgst,
        cgst_amount: Math.round(cgstAmt * 100) / 100,
        sgst_rate: sgst,
        sgst_amount: Math.round(sgstAmt * 100) / 100,
        igst_rate: igst,
        igst_amount: Math.round(igstAmt * 100) / 100,
        total_amount: Math.round(totalLine * 100) / 100
    };

    currentCart.push(item);
    renderPosCart();
    
    // Reset item inputs
    qtyInput.value = "1";
    discInput.value = "0";
}

function removePosItem(index) {
    currentCart.splice(index, 1);
    renderPosCart();
}

function renderPosCart() {
    const tbody = document.getElementById("pos-cart-tbody");
    if (!tbody) return;

    if (currentCart.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted" style="padding: 24px;">No items added yet. Search or select a product above.</td></tr>';
        updatePosTotals(0, 0, 0, 0);
        return;
    }

    let totTaxable = 0, totCgst = 0, totSgst = 0, totGross = 0;

    tbody.innerHTML = currentCart.map((item, idx) => {
        totTaxable += item.taxable_amount;
        totCgst += item.cgst_amount;
        totSgst += item.sgst_amount;
        totGross += item.total_amount;

        return `
            <tr>
                <td class="text-center">${idx + 1}</td>
                <td><b>${item.product_name}</b><br/><small class="text-muted">HSN: ${item.hsn_code||'-'}</small></td>
                <td><span class="badge badge-fefo">${item.batch_no}</span></td>
                <td>${item.exp_date||'-'}</td>
                <td class="text-center">${item.qty} ${item.unit_name||''}</td>
                <td class="text-right">₹${item.sale_rate.toFixed(2)}</td>
                <td class="text-right">₹${item.taxable_amount.toFixed(2)}</td>
                <td class="text-right"><b>₹${item.total_amount.toFixed(2)}</b></td>
                <td class="text-center"><button class="btn btn-danger btn-sm" onclick="removePosItem(${idx})">✕</button></td>
            </tr>
        `;
    }).join("");

    updatePosTotals(totTaxable, totCgst, totSgst, totGross);
}

function updatePosTotals(taxable, cgst, sgst, gross) {
    const netRound = Math.round(gross);
    const roundOff = Math.round((netRound - gross) * 100) / 100;

    document.getElementById("pos-tot-taxable").innerText = `₹${taxable.toFixed(2)}`;
    document.getElementById("pos-tot-gst").innerText = `₹${(cgst + sgst).toFixed(2)}`;
    document.getElementById("pos-tot-round").innerText = `₹${roundOff.toFixed(2)}`;
    document.getElementById("pos-grand-total").innerText = `₹${netRound.toFixed(2)}`;

    const paidInput = document.getElementById("pos-paid-amount");
    if (paidInput) paidInput.value = netRound;
}

async function submitSalesBill() {
    if (currentCart.length === 0) {
        alert("Cart is empty! Add at least one item.");
        return;
    }

    const custName = document.getElementById("pos-cust-name").value.trim();
    if (!custName) {
        alert("Please enter Farmer / Customer Name.");
        document.getElementById("pos-cust-name").focus();
        return;
    }

    const mobile = document.getElementById("pos-cust-mobile").value.trim();
    const village = document.getElementById("pos-cust-village").value.trim();

    // Check if farmer already exists in database, otherwise auto-create them on the fly
    let custId = null;
    const existing = allCustomers.find(c => c.customer_name.toLowerCase() === custName.toLowerCase());
    if (existing) {
        custId = existing.customer_id;
    } else {
        try {
            const custRes = await fetch("/api/masters/customers", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    customer_name: custName,
                    mobile: mobile,
                    village: village,
                    opening_balance: 0.0
                })
            });
            const custData = await custRes.json();
            if (custRes.ok && custData.success) {
                custId = custData.customer_id;
                // Add to local list
                allCustomers.push({
                    customer_id: custId,
                    customer_name: custName,
                    mobile: mobile,
                    village: village,
                    current_balance: 0.0
                });
                await refreshCustomerList();
            } else {
                alert("Failed to auto-register farmer: " + (custData.detail || "Error"));
                return;
            }
        } catch (err) {
            alert("Error auto-saving farmer: " + err.message);
            return;
        }
    }

    const invNo = document.getElementById("pos-inv-no").value;
    const saleDate = document.getElementById("pos-date").value;
    const payMode = document.getElementById("pos-pay-mode").value;
    const paidAmt = parseFloat(document.getElementById("pos-paid-amount").value) || 0;
    const remarks = document.getElementById("pos-remarks").value;
    const crop = document.getElementById("pos-cust-crop") ? document.getElementById("pos-cust-crop").value.trim() : "";

    let totTaxable = 0, totCgst = 0, totSgst = 0, totIgst = 0, totDisc = 0, gross = 0;
    currentCart.forEach(i => {
        totTaxable += i.taxable_amount;
        totCgst += i.cgst_amount;
        totSgst += i.sgst_amount;
        totIgst += i.igst_amount;
        totDisc += i.discount_amount;
        gross += i.total_amount;
    });

    const netAmount = Math.round(gross);
    const roundOff = Math.round((netAmount - gross) * 100) / 100;

    const salePayload = {
        invoice_no: invNo,
        sale_date: saleDate,
        customer_id: custId,
        doctor_or_officer: crop || "ऊस / सर्व पिके",
        payment_mode: payMode,
        total_taxable: Math.round(totTaxable * 100) / 100,
        total_cgst: Math.round(totCgst * 100) / 100,
        total_sgst: Math.round(totSgst * 100) / 100,
        total_igst: Math.round(totIgst * 100) / 100,
        total_discount: Math.round(totDisc * 100) / 100,
        round_off: roundOff,
        net_amount: netAmount,
        paid_amount: paidAmt,
        due_amount: Math.max(0, netAmount - paidAmt),
        remarks: remarks,
        items: currentCart
    };

    try {
        const res = await fetch("/api/sales/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(salePayload)
        });
        const result = await res.json();

        if (res.ok && result.success) {
            // Open PDF Tax Invoice in a new tab for printing
            window.open(`/api/sales/${result.sale_id}/pdf`, "_blank");
            alert(`✓ Bill ${invNo} saved for ${custName}!`);
            resetPosCart();
            await refreshProductList();
            await refreshCustomerList();
            await fetchNextInvoiceNo();
        } else {
            alert(`Error: ${result.detail || "Failed to save bill"}`);
        }
    } catch (err) {
        console.error(err);
        alert("Failed to submit bill: " + err.message);
    }
}

function resetPosCart() {
    currentCart = [];
    renderPosCart();
    document.getElementById("pos-cust-name").value = "";
    document.getElementById("pos-cust-mobile").value = "";
    document.getElementById("pos-cust-village").value = "";
    if (document.getElementById("pos-cust-crop")) document.getElementById("pos-cust-crop").value = "";
    document.getElementById("pos-remarks").value = "";
}

// ----------------- Inward Purchase Tab -----------------
async function submitPurchase() {
    const suppId = parseInt(document.getElementById("pur-supplier").value);
    const invNo = document.getElementById("pur-inv-no").value;
    const purDate = document.getElementById("pur-date").value;
    const prodId = parseInt(document.getElementById("pur-item-product").value);
    const batchNo = document.getElementById("pur-batch-no").value;
    const expDate = document.getElementById("pur-exp-date").value;
    const qty = parseFloat(document.getElementById("pur-qty").value);
    const freeQty = parseFloat(document.getElementById("pur-free-qty").value) || 0;
    const purRate = parseFloat(document.getElementById("pur-rate").value);
    const saleRate = parseFloat(document.getElementById("pur-sale-rate").value);
    const mrp = parseFloat(document.getElementById("pur-mrp").value);

    if (!suppId || !invNo || !prodId || !batchNo || isNaN(qty) || qty <= 0 || isNaN(purRate)) {
        alert("Please fill in all mandatory purchase fields.");
        return;
    }

    const taxable = qty * purRate;
    const net = taxable; // simplified standard purchase calculation

    const purchasePayload = {
        invoice_no: invNo,
        purchase_date: purDate,
        supplier_id: suppId,
        payment_type: "CREDIT",
        total_taxable: taxable,
        net_amount: net,
        paid_amount: 0.0,
        due_amount: net,
        items: [
            {
                product_id: prodId,
                batch_no: batchNo,
                exp_date: expDate,
                qty: qty,
                free_qty: freeQty,
                purchase_rate: purRate,
                sale_rate: saleRate,
                mrp: mrp,
                taxable_amount: taxable,
                total_amount: net
            }
        ]
    };

    try {
        const res = await fetch("/api/purchase/create", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(purchasePayload)
        });
        const data = await res.json();
        if (res.ok) {
            alert(`Inward Purchase recorded! Batch ${batchNo} added to stock.`);
            await refreshProductList();
            document.getElementById("pur-batch-no").value = "";
            document.getElementById("pur-qty").value = "";
        } else {
            alert("Error: " + data.detail);
        }
    } catch (err) {
        alert("Error submitting purchase: " + err.message);
    }
}

// ----------------- Inventory Tab & Stock Management -----------------
let rawInventoryItems = [];

async function loadInventory() {
    try {
        const res = await fetch("/api/inventory/stock-summary");
        rawInventoryItems = await res.json();
        filterInventoryTable();

        // Load Expiry Alerts
        const alertRes = await fetch("/api/inventory/expiry-alerts?days=90");
        const alerts = await alertRes.json();
        const alertBox = document.getElementById("inv-expiry-alerts");
        if (alertBox) {
            if (alerts.length === 0) {
                alertBox.innerHTML = '<span class="badge badge-success">✓ No products expiring within 90 days.</span>';
            } else {
                alertBox.innerHTML = alerts.map(a => `
                    <span class="badge badge-expiring" style="margin-right: 6px; padding: 4px 8px; display: inline-block; margin-bottom: 4px;">
                        ⚠️ <b>${a.product_name}</b> (Batch: ${a.batch_no}) Exp: ${a.exp_date} (In ${a.days_to_expiry} days) - Stock: ${a.current_qty}
                    </span>
                `).join("");
            }
        }
    } catch (err) {
        console.error("Failed to load inventory:", err);
    }
}

function filterInventoryTable() {
    const tbody = document.getElementById("inv-table-tbody");
    if (!tbody) return;

    const catFilter = document.getElementById("inv-filter-cat")?.value || "";
    const search = document.getElementById("inv-search-input")?.value.trim().toLowerCase() || "";

    let filtered = rawInventoryItems || [];
    if (catFilter) {
        filtered = filtered.filter(item => String(item.category_id) === String(catFilter));
    }
    if (search) {
        filtered = filtered.filter(item => 
            (item.product_name || "").toLowerCase().includes(search) ||
            (item.batch_no || "").toLowerCase().includes(search) ||
            (item.manufacturer_name || "").toLowerCase().includes(search) ||
            (item.category_name || "").toLowerCase().includes(search)
        );
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted" style="padding: 20px;">No stock records found matching filters. Click <b>+ Add Stock</b> to add new inventory.</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(item => `
        <tr>
            <td><b>${item.product_name}</b></td>
            <td><span class="badge" style="background:#e0f2fe; color:#0369a1; font-size:11px;">${item.category_name || '-'}</span></td>
            <td>${item.manufacturer_name || '-'}</td>
            <td><span class="badge badge-fefo">${item.batch_no}</span></td>
            <td>${item.exp_date || '-'}</td>
            <td class="text-center font-bold" style="color: ${item.current_qty <= 5 ? '#dc2626' : '#15803d'}; font-size: 13.5px;">
                <b>${item.current_qty}</b> ${item.unit_symbol || ''}
            </td>
            <td class="text-right">₹${Number(item.purchase_rate || 0).toFixed(2)}</td>
            <td class="text-right" style="font-weight:600; color:#047857;">₹${Number(item.sale_rate || 0).toFixed(2)}</td>
            <td class="text-right" style="font-weight:700;">₹${Number(item.purchase_value || 0).toFixed(2)}</td>
            <td class="text-center">
                <button class="btn btn-primary btn-sm" onclick="openAddStockModal(${item.product_id}, '${item.batch_no}', ${item.purchase_rate || 0}, ${item.sale_rate || 0}, ${item.mrp || item.sale_rate || 0}, '${item.exp_date || ''}')" style="padding: 3px 8px; font-size: 11px;">
                    + Add Qty
                </button>
            </td>
        </tr>
    `).join("");
}

// ----------------- Add Direct Stock Modal Logic -----------------
function populateStockProductDropdown() {
    const sel = document.getElementById("stock-prod-select");
    if (!sel) return;

    if (!allProducts || allProducts.length === 0) {
        sel.innerHTML = '<option value="">No products available. Please add products in catalog first.</option>';
        return;
    }

    sel.innerHTML = '<option value="">-- Select Product (उत्पाद निवडा) --</option>' + 
        allProducts.map(p => `<option value="${p.product_id}">${p.product_name} (${p.category_name || ''} • ${p.unit_symbol || ''})</option>`).join("");
}

function openAddStockModal(productId = null, batchNo = "", purRate = 0, saleRate = 0, mrp = 0, expDate = "") {
    populateStockProductDropdown();
    const modal = document.getElementById("modal-add-stock");
    if (!modal) return;
    modal.style.display = "flex";

    const prodSelect = document.getElementById("stock-prod-select");
    const qtyInput = document.getElementById("stock-add-qty");
    const batchInput = document.getElementById("stock-add-batch");
    const purInput = document.getElementById("stock-add-pur-rate");
    const saleInput = document.getElementById("stock-add-sale-rate");
    const mrpInput = document.getElementById("stock-add-mrp");
    const expInput = document.getElementById("stock-add-exp");
    const mfgInput = document.getElementById("stock-add-mfg");
    const remarksInput = document.getElementById("stock-add-remarks");

    qtyInput.value = "";
    remarksInput.value = "Direct Stock Addition";

    const todayStr = new Date().toISOString().split("T")[0];
    if (mfgInput) mfgInput.value = todayStr;

    if (productId) {
        prodSelect.value = productId;
        batchInput.value = batchNo || "";
        purInput.value = purRate || "";
        saleInput.value = saleRate || "";
        mrpInput.value = mrp || "";
        expInput.value = (expDate && expDate !== "-") ? expDate : "";
    } else {
        prodSelect.value = "";
        batchInput.value = "";
        purInput.value = "";
        saleInput.value = "";
        mrpInput.value = "";
        expInput.value = "";
    }

    setTimeout(() => {
        if (productId) {
            qtyInput.focus();
        } else {
            prodSelect.focus();
        }
    }, 150);
}

function closeAddStockModal() {
    const modal = document.getElementById("modal-add-stock");
    if (modal) modal.style.display = "none";
}

function onStockProductChanged() {
    const prodId = Number(document.getElementById("stock-prod-select")?.value);
    if (!prodId) return;

    const prod = allProducts.find(p => p.product_id === prodId);
    if (!prod) return;

    const purInput = document.getElementById("stock-add-pur-rate");
    const saleInput = document.getElementById("stock-add-sale-rate");
    const mrpInput = document.getElementById("stock-add-mrp");
    const batchInput = document.getElementById("stock-add-batch");

    if (purInput) purInput.value = prod.default_purchase_rate || 0;
    if (saleInput) saleInput.value = prod.default_sale_rate || 0;
    if (mrpInput) mrpInput.value = prod.mrp || prod.default_sale_rate || 0;

    if (batchInput && !batchInput.value) {
        const todayNum = new Date().toISOString().slice(2,10).replace(/-/g, "");
        batchInput.value = `STK-${todayNum}-${prodId}`;
    }
}

async function submitAddDirectStock() {
    const prodId = Number(document.getElementById("stock-prod-select")?.value);
    const qty = parseFloat(document.getElementById("stock-add-qty")?.value || "0");
    const batchNo = document.getElementById("stock-add-batch")?.value.trim() || "";
    const purRate = parseFloat(document.getElementById("stock-add-pur-rate")?.value || "0");
    const saleRate = parseFloat(document.getElementById("stock-add-sale-rate")?.value || "0");
    const mrp = parseFloat(document.getElementById("stock-add-mrp")?.value || "0");
    const expDate = document.getElementById("stock-add-exp")?.value || null;
    const mfgDate = document.getElementById("stock-add-mfg")?.value || null;
    const remarks = document.getElementById("stock-add-remarks")?.value.trim() || "Manual Stock Addition";
    const btnSubmit = document.getElementById("btn-save-stock");

    if (!prodId) {
        alert("कृपया Product निवडा (Please select a product).");
        return;
    }
    if (!qty || qty <= 0) {
        alert("कृपया 0 पेक्षा जास्त संख्या टाका (Quantity must be greater than 0).");
        return;
    }

    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.textContent = "⏳ सेव्ह होत आहे...";
    }

    try {
        const res = await fetch("/api/inventory/add-stock", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                product_id: prodId,
                qty: qty,
                batch_no: batchNo || null,
                purchase_rate: purRate,
                sale_rate: saleRate,
                mrp: mrp,
                mfg_date: mfgDate,
                exp_date: expDate,
                remarks: remarks
            })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            alert(`✓ ${data.message || "स्टॉक यशस्वीरीत्या जमा झाला आहे!"}`);
            closeAddStockModal();
            await loadInventory();
            await refreshProductList();
        } else {
            alert("त्रुटी: " + (data.detail || "स्टॉक जमा करता आला नाही."));
        }
    } catch (err) {
        console.error("Failed to add stock:", err);
        alert("सर्व्हरशी संपर्क होऊ शकला नाही: " + err.message);
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.textContent = "+ Save Stock (स्टॉक सेव्ह करा)";
        }
    }
}


// ----------------- Accounts & Day Book Tab -----------------
async function loadDayBook() {
    const today = new Date().toISOString().split("T")[0];
    const dateInput = document.getElementById("acc-daybook-date");
    const dateStr = dateInput ? dateInput.value || today : today;
    if (dateInput && !dateInput.value) dateInput.value = today;

    try {
        const res = await fetch(`/api/accounting/day-book?date=${dateStr}`);
        const data = await res.json();

        document.getElementById("db-sales").innerText = `₹${data.total_sales.toFixed(2)} (${data.sales_count} bills)`;
        document.getElementById("db-purchases").innerText = `₹${data.total_purchases.toFixed(2)} (${data.purchases_count} inwards)`;
        document.getElementById("db-expenses").innerText = `₹${data.total_expenses.toFixed(2)}`;
    } catch (err) {
        console.error(err);
    }
}

async function submitCustomerReceipt() {
    const custId = parseInt(document.getElementById("acc-receipt-cust").value);
    const amount = parseFloat(document.getElementById("acc-receipt-amt").value);
    const mode = document.getElementById("acc-receipt-mode").value;
    const dateStr = document.getElementById("acc-receipt-date").value || new Date().toISOString().split("T")[0];

    if (!custId || isNaN(amount) || amount <= 0) {
        alert("Please select customer and valid amount");
        return;
    }

    try {
        const res = await fetch("/api/accounting/customer-receipt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ customer_id: custId, receipt_date: dateStr, amount: amount, payment_mode: mode })
        });
        if (res.ok) {
            alert(`Receipt of ₹${amount} recorded! Customer ledger updated.`);
            document.getElementById("acc-receipt-amt").value = "";
            await refreshCustomerList();
            await loadDayBook();
        }
    } catch (err) {
        alert(err.message);
    }
}

// ----------------- GST Reports Tab -----------------
async function loadGSTR1() {
    const fromDate = document.getElementById("gst-from-date").value || "2026-01-01";
    const toDate = document.getElementById("gst-to-date").value || new Date().toISOString().split("T")[0];

    try {
        // 1. GSTR-1 B2B
        const b2bRes = await fetch(`/api/gst/gstr1-b2b?from_date=${fromDate}&to_date=${toDate}`);
        const b2bData = await b2bRes.json();
        const b2bTbody = document.getElementById("gst-b2b-tbody");
        if (b2bTbody) {
            b2bTbody.innerHTML = b2bData.map(r => `
                <tr>
                    <td><b>${r.receiver_gstin}</b></td>
                    <td>${r.receiver_name}</td>
                    <td>${r.invoice_no}</td>
                    <td>${r.invoice_date}</td>
                    <td class="text-right">₹${r.invoice_value.toFixed(2)}</td>
                    <td class="text-right">₹${r.total_taxable.toFixed(2)}</td>
                    <td class="text-right">₹${(r.total_cgst + r.total_sgst).toFixed(2)}</td>
                </tr>
            `).join("");
        }

        // 2. HSN Summary
        const hsnRes = await fetch(`/api/gst/hsn-summary?from_date=${fromDate}&to_date=${toDate}`);
        const hsnData = await hsnRes.json();
        const hsnTbody = document.getElementById("gst-hsn-tbody");
        if (hsnTbody) {
            hsnTbody.innerHTML = hsnData.map(r => `
                <tr>
                    <td><b>${r.hsn_code}</b></td>
                    <td>${r.product_name}</td>
                    <td>${r.uqc||''}</td>
                    <td class="text-center">${r.total_qty}</td>
                    <td class="text-right">₹${r.total_taxable.toFixed(2)}</td>
                    <td class="text-right">₹${(r.total_cgst + r.total_sgst).toFixed(2)}</td>
                    <td class="text-right">₹${r.total_amount.toFixed(2)}</td>
                </tr>
            `).join("");
        }
    } catch (err) {
        console.error(err);
    }
}

// ----------------- Master Data Tab -----------------
async function loadMasterTables() {
    await refreshProductList();
    filterProductCatalog();
}

function filterProductCatalog() {
    const searchInput = document.getElementById("m-prod-search");
    const catSelect = document.getElementById("m-prod-filter-cat");
    const countEl = document.getElementById("m-prod-count");
    const tbody = document.getElementById("m-prod-tbody");

    if (!tbody) return;

    const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
    const catFilter = catSelect ? catSelect.value : "";

    let filtered = allProducts || [];
    if (query) {
        filtered = filtered.filter(p => 
            (p.product_name && p.product_name.toLowerCase().includes(query)) ||
            (p.hsn_code && p.hsn_code.toLowerCase().includes(query)) ||
            (p.manufacturer_name && p.manufacturer_name.toLowerCase().includes(query)) ||
            (p.category_name && p.category_name.toLowerCase().includes(query))
        );
    }
    if (catFilter) {
        filtered = filtered.filter(p => String(p.category_id) === String(catFilter));
    }

    if (countEl) {
        countEl.textContent = filtered.length;
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center" style="padding: 24px; color: #64748b;">No products found matching "${query || 'filter'}".</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => {
        const stockVal = parseFloat(p.total_stock) || 0;
        let stockBadge = `<span class="badge badge-success">${stockVal} ${p.unit_symbol || 'Nos'}</span>`;
        if (stockVal <= 0) {
            stockBadge = `<span class="badge badge-danger">0 Out of Stock</span>`;
        } else if (stockVal <= (p.min_stock_alert || 5)) {
            stockBadge = `<span class="badge badge-warning">${stockVal} ${p.unit_symbol || 'Nos'} (Low)</span>`;
        }

        const purRate = parseFloat(p.default_purchase_rate) || 0;
        const saleRate = parseFloat(p.default_sale_rate) || 0;
        const mrp = parseFloat(p.default_mrp) || 0;

        return `
            <tr>
                <td>
                    <div style="font-weight: 700; color: #1e293b;">${p.product_name}</div>
                    <small style="color: #64748b;">ID: #${p.product_id} • GST: ${((p.cgst_rate||0)+(p.sgst_rate||0)+(p.igst_rate||0))}%</small>
                </td>
                <td><span class="badge" style="background:#e0f2fe; color:#0369a1; font-weight:600;">${p.category_name || 'General'}</span></td>
                <td><span style="font-weight: 500;">${p.manufacturer_name || '-'}</span></td>
                <td><code>${p.hsn_code || '-'}</code></td>
                <td class="text-right" style="color: #475569;">₹${purRate.toFixed(2)}</td>
                <td class="text-right" style="font-weight: 700; color: #047857;">₹${saleRate.toFixed(2)}</td>
                <td class="text-right" style="color: #334155;">₹${mrp.toFixed(2)}</td>
                <td class="text-center">${stockBadge}</td>
            </tr>
        `;
    }).join("");
}

async function createMasterProduct() {
    const name = document.getElementById("m-prod-name").value.trim();
    const catId = parseInt(document.getElementById("m-prod-cat").value) || null;
    const mfgId = parseInt(document.getElementById("m-prod-mfg").value) || null;
    const hsn = document.getElementById("m-prod-hsn").value.trim();
    const unitId = parseInt(document.getElementById("m-prod-unit").value) || 1;
    const taxId = parseInt(document.getElementById("m-prod-tax").value) || 2;
    const purRate = parseFloat(document.getElementById("m-prod-pur-rate").value) || 0;
    const saleRate = parseFloat(document.getElementById("m-prod-sale-rate").value) || 0;
    const mrp = parseFloat(document.getElementById("m-prod-mrp").value) || 0;
    const alertQty = parseFloat(document.getElementById("m-prod-alert")?.value) || 5;

    if (!name) {
        alert("Product Name is required!");
        return;
    }

    try {
        const res = await fetch("/api/masters/products", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                product_name: name,
                category_id: catId,
                manufacturer_id: mfgId,
                hsn_code: hsn,
                unit_id: unitId,
                tax_group_id: taxId,
                default_purchase_rate: purRate,
                default_sale_rate: saleRate,
                default_mrp: mrp,
                min_stock_alert: alertQty
            })
        });
        if (res.ok) {
            alert(`✅ Product "${name}" saved to catalog successfully!`);
            document.getElementById("m-prod-name").value = "";
            document.getElementById("m-prod-hsn").value = "";
            document.getElementById("m-prod-pur-rate").value = "0";
            document.getElementById("m-prod-sale-rate").value = "0";
            document.getElementById("m-prod-mrp").value = "0";
            if (document.getElementById("m-prod-alert")) document.getElementById("m-prod-alert").value = "5";
            await loadMasterTables();
        } else {
            const err = await res.json();
            alert("Failed to save product: " + (err.detail || "Server error"));
        }
    } catch (err) {
        alert("Network error: " + err.message);
    }
}

// ----------------- Farmer Status & Khata Tab -----------------
async function loadFarmerStatusList() {
    try {
        // 1. Fetch villages for filter dropdown
        const villRes = await fetch("/api/masters/farmers/villages");
        const villages = await villRes.json();
        const villSelect = document.getElementById("fs-filter-village");
        if (villSelect) {
            const curVal = villSelect.value;
            villSelect.innerHTML = '<option value="">All Villages (सर्व गावे)</option>' + 
                villages.map(v => `<option value="${v}">${v}</option>`).join("");
            villSelect.value = curVal;
        }

        // 2. Fetch all farmers status
        const res = await fetch("/api/masters/farmers/status-list");
        farmerStatusList = await res.json();
        filterFarmerStatusList();
    } catch (err) {
        console.error("Error loading farmer status list:", err);
    }
}

function toggleOnlyCreditFilter() {
    isOnlyCreditFilter = !isOnlyCreditFilter;
    const btn = document.getElementById("fs-btn-credit-toggle");
    if (btn) {
        if (isOnlyCreditFilter) {
            btn.className = "btn btn-danger";
            btn.innerText = "✓ Showing Pending Khata Only (Clear)";
        } else {
            btn.className = "btn btn-secondary";
            btn.innerText = "⚠️ Show Only Pending Khata";
        }
    }
    filterFarmerStatusList();
}

function filterFarmerStatusList() {
    const searchName = (document.getElementById("fs-search-name").value || "").trim().toLowerCase();
    const selectedVillage = (document.getElementById("fs-filter-village").value || "").trim().toLowerCase();

    let filtered = farmerStatusList.filter(f => {
        const matchesName = !searchName || 
            f.customer_name.toLowerCase().includes(searchName) || 
            (f.mobile && f.mobile.includes(searchName));
        const matchesVillage = !selectedVillage || (f.village && f.village.toLowerCase() === selectedVillage);
        const matchesCredit = !isOnlyCreditFilter || (f.current_balance > 0);

        return matchesName && matchesVillage && matchesCredit;
    });

    // Update Top KPIs
    let totSales = 0, totPending = 0;
    farmerStatusList.forEach(f => {
        totSales += f.total_purchases_amount;
        if (f.current_balance > 0) totPending += f.current_balance;
    });

    document.getElementById("fs-total-farmers").innerText = farmerStatusList.length;
    document.getElementById("fs-total-sales").innerText = `₹${totSales.toFixed(2)}`;
    document.getElementById("fs-total-pending").innerText = `₹${totPending.toFixed(2)}`;

    // Render Table
    const tbody = document.getElementById("fs-farmers-tbody");
    if (!tbody) return;

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding: 24px;">No matching farmers found.</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(f => {
        const hasDue = f.current_balance > 0;
        return `
            <tr style="cursor: pointer;" onclick="openFarmerDetail(${f.customer_id})">
                <td><b>${f.customer_name}</b></td>
                <td><span class="badge badge-fefo">${f.village}</span></td>
                <td>${f.mobile || '-'}</td>
                <td class="text-center">${f.total_bills_count} bills</td>
                <td class="text-right">₹${f.total_purchases_amount.toFixed(2)}</td>
                <td class="text-right">₹${f.total_paid_amount.toFixed(2)}</td>
                <td class="text-right">
                    ${hasDue ? `<b style="color: var(--danger); font-size: 13.5px;">₹${f.current_balance.toFixed(2)}</b>` : `<span class="badge badge-success">₹0.00 (Nil)</span>`}
                </td>
                <td class="text-center">
                    <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openFarmerDetail(${f.customer_id})">
                        🔍 View Statement
                    </button>
                </td>
            </tr>
        `;
    }).join("");
}

// ----------------- Farmer Statement Modal -----------------
async function openFarmerDetail(customerId) {
    activeFarmerId = customerId;
    try {
        const res = await fetch(`/api/masters/farmers/${customerId}/statement`);
        const data = await res.json();
        if (!res.ok) {
            alert("Failed to load farmer statement");
            return;
        }

        const c = data.customer;
        document.getElementById("fd-name").innerText = `👨‍🌾 ${c.customer_name}`;
        document.getElementById("fd-meta").innerText = `Village: ${c.village || 'Local'} | Taluka: ${c.taluka || '-'} | Mobile: ${c.mobile || '-'}`;
        document.getElementById("fd-pending-balance").innerText = `₹${c.current_balance.toFixed(2)}`;
        
        let totPurchases = 0;
        data.invoices.forEach(inv => totPurchases += inv.net_amount);
        document.getElementById("fd-tot-purchases").innerText = `₹${totPurchases.toFixed(2)}`;

        // Pre-fill payment input with pending balance
        document.getElementById("fd-pay-amount").value = c.current_balance > 0 ? c.current_balance : "";

        // Render Invoices & Goods List
        const invTbody = document.getElementById("fd-invoices-tbody");
        if (data.invoices.length === 0) {
            invTbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding: 16px;">No bills generated yet for this farmer.</td></tr>';
        } else {
            invTbody.innerHTML = data.invoices.map(inv => {
                const goodsListHtml = inv.items.map(it => 
                    `<div>• <b>${it.product_name}</b> <span class="text-muted">(Batch: ${it.batch_no})</span> — <b>${it.qty} ${it.unit_symbol||''}</b> @ ₹${it.sale_rate} = ₹${it.total_amount}</div>`
                ).join("");

                return `
                    <tr>
                        <td><b>${inv.invoice_no}</b></td>
                        <td>${inv.sale_date}</td>
                        <td style="font-size: 12px;">${goodsListHtml}</td>
                        <td class="text-right">₹${inv.net_amount.toFixed(2)}</td>
                        <td class="text-right">₹${inv.paid_amount.toFixed(2)}</td>
                        <td class="text-right" style="color: ${inv.due_amount > 0 ? 'var(--danger)' : 'inherit'}; font-weight: 700;">₹${inv.due_amount.toFixed(2)}</td>
                        <td class="text-center">
                            <a href="/api/sales/${inv.sale_id}/pdf" target="_blank" class="btn btn-secondary btn-sm" style="text-decoration: none;">🖨️ PDF</a>
                        </td>
                    </tr>
                `;
            }).join("");
        }

        // Render Receipts
        const recTbody = document.getElementById("fd-receipts-tbody");
        if (data.receipts.length === 0) {
            recTbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted" style="padding: 12px;">No payment receipts recorded yet.</td></tr>';
        } else {
            recTbody.innerHTML = data.receipts.map(r => `
                <tr>
                    <td><b>${r.voucher_no}</b></td>
                    <td>${r.voucher_date}</td>
                    <td>${r.narration || 'Payment received'}</td>
                    <td class="text-right" style="color: var(--success); font-weight: 700;">₹${r.total_amount.toFixed(2)}</td>
                </tr>
            `).join("");
        }

        // Show Modal
        document.getElementById("modal-farmer-detail").classList.add("show");
    } catch (err) {
        console.error(err);
        alert("Error: " + err.message);
    }
}

function closeFarmerDetailModal() {
    document.getElementById("modal-farmer-detail").classList.remove("show");
    activeFarmerId = null;
}

async function submitQuickFarmerPayment() {
    if (!activeFarmerId) return;
    const amount = parseFloat(document.getElementById("fd-pay-amount").value);
    const mode = document.getElementById("fd-pay-mode").value;
    const today = new Date().toISOString().split("T")[0];

    if (isNaN(amount) || amount <= 0) {
        alert("Please enter a valid payment amount greater than 0.");
        return;
    }

    try {
        const res = await fetch("/api/accounting/customer-receipt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                customer_id: activeFarmerId,
                receipt_date: today,
                amount: amount,
                payment_mode: mode,
                narration: "Direct collection from Farmer Status Ledger"
            })
        });

        if (res.ok) {
            alert(`✓ Payment of ₹${amount} recorded successfully!`);
            await openFarmerDetail(activeFarmerId);
            await loadFarmerStatusList();
            await refreshCustomerList();
        } else {
            const data = await res.json();
            alert("Failed to record payment: " + (data.detail || "Error"));
        }
    } catch (err) {
        alert("Payment Error: " + err.message);
    }
}

function sendWhatsAppPaymentReminder() {
    if (!activeFarmerId) return;
    const farmer = farmerStatusList.find(f => f.customer_id === activeFarmerId);
    if (!farmer) return;

    if (farmer.current_balance <= 0) {
        alert("This farmer has zero pending balance (Nil).");
        return;
    }

    const mobile = (farmer.mobile || "").replace(/\D/g, "");
    const phoneParam = mobile.length === 10 ? `91${mobile}` : mobile;
    const text = encodeURIComponent(
        `नमस्कार ${farmer.customer_name} जी, 🌱 कृषीधन कृषी सेवा केंद्र कडे आपले एकूण ₹${farmer.current_balance.toFixed(2)} उधारी (बाकी) रक्कम बाकी आहे. कृपया त्वरित जमा करावी. धन्यवाद!`
    );

    const waUrl = phoneParam 
        ? `https://api.whatsapp.com/send?phone=${phoneParam}&text=${text}`
        : `https://api.whatsapp.com/send?text=${text}`;

    window.open(waUrl, "_blank");
}

// ----------------- Settings & Backup Tab -----------------
async function loadSettings() {
    try {
        const res = await fetch("/api/system/settings");
        const s = await res.json();
        document.getElementById("set-shop-name").value = s.company_name || "";
        document.getElementById("set-gstin").value = s.gstin || "";
        document.getElementById("set-address").value = s.address || "";
        document.getElementById("set-city").value = s.city || "";
        document.getElementById("set-mobile").value = s.mobile || "";
        document.getElementById("set-lic-fert").value = s.dl_fertilizer || "";
        document.getElementById("set-lic-pest").value = s.dl_pesticide || "";
        document.getElementById("set-lic-seed").value = s.dl_seed || "";
        document.getElementById("set-terms").value = s.invoice_terms || "";
    } catch (err) {
        console.error(err);
    }
}

async function saveSettings() {
    const payload = {
        company_name: document.getElementById("set-shop-name").value,
        gstin: document.getElementById("set-gstin").value,
        address: document.getElementById("set-address").value,
        city: document.getElementById("set-city").value,
        mobile: document.getElementById("set-mobile").value,
        dl_fertilizer: document.getElementById("set-lic-fert").value,
        dl_pesticide: document.getElementById("set-lic-pest").value,
        dl_seed: document.getElementById("set-lic-seed").value,
        invoice_terms: document.getElementById("set-terms").value
    };

    try {
        const res = await fetch("/api/system/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (res.ok) alert("Shop settings and license numbers saved successfully!");
    } catch (err) {
        alert(err.message);
    }
}

async function triggerDatabaseBackup() {
    try {
        const res = await fetch("/api/system/backup", { method: "POST" });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(`✓ Backup created successfully!\nLocation: ${data.file_path}`);
        } else {
            alert("Backup failed: " + data.detail);
        }
    } catch (err) {
        alert("Backup error: " + err.message);
    }
}

// ----------------- Profit & Loss Workspace -----------------
function setPnLPeriod(period) {
    const today = new Date();
    const todayStr = today.toISOString().split("T")[0];
    const fromInput = document.getElementById("pnl-from-date");
    const toInput = document.getElementById("pnl-to-date");

    if (period === "today") {
        fromInput.value = todayStr;
        toInput.value = todayStr;
    } else if (period === "week") {
        const weekAgo = new Date(today);
        weekAgo.setDate(today.getDate() - 7);
        fromInput.value = weekAgo.toISOString().split("T")[0];
        toInput.value = todayStr;
    } else if (period === "month") {
        fromInput.value = todayStr.substring(0, 8) + "01";
        toInput.value = todayStr;
    } else if (period === "year") {
        const curYear = today.getFullYear();
        fromInput.value = `${curYear}-04-01`;
        toInput.value = `${curYear + 1}-03-31`;
    } else if (period === "all") {
        fromInput.value = "2020-01-01";
        toInput.value = "2030-12-31";
    }
    loadProfitAndLoss();
}

async function loadProfitAndLoss() {
    const fromDate = document.getElementById("pnl-from-date")?.value || new Date().toISOString().split("T")[0].substring(0, 8) + "01";
    const toDate = document.getElementById("pnl-to-date")?.value || new Date().toISOString().split("T")[0];

    try {
        // 1. Fetch High-Level P&L Summary & Categories
        const res = await fetch(`/api/accounting/profit-and-loss?from_date=${fromDate}&to_date=${toDate}`);
        const data = await res.json();

        // 2. Update KPI Cards
        document.getElementById("pnl-kpi-sales").innerText = `₹${(data.sales_revenue || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById("pnl-kpi-invoices").innerText = data.total_invoices || 0;
        document.getElementById("pnl-kpi-disc").innerText = `₹${(data.total_discount || 0).toFixed(0)}`;
        
        document.getElementById("pnl-kpi-cogs").innerText = `₹${(data.cogs || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        document.getElementById("pnl-kpi-gp").innerText = `₹${(data.gross_profit || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById("pnl-kpi-gp-pct").innerText = `${data.gross_margin_pct || 0}% Margin`;
        
        document.getElementById("pnl-kpi-exp").innerText = `₹${(data.total_expenses || 0).toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        
        const npEl = document.getElementById("pnl-kpi-np");
        const npVal = data.net_profit || 0;
        npEl.innerText = `₹${npVal.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        if (npVal < 0) {
            npEl.style.color = "#dc2626"; // Red for Loss
        } else {
            npEl.style.color = "#7e22ce"; // Purple/Green for Net Profit
        }
        document.getElementById("pnl-kpi-np-pct").innerText = `${data.net_margin_pct || 0}% Net Margin`;

        // 3. Render Multi-Step Trading & P&L Statement
        const stmtTbody = document.getElementById("pnl-statement-tbody");
        if (stmtTbody) {
            let expDetails = "";
            if (data.expenses_breakdown && data.expenses_breakdown.length > 0) {
                expDetails = data.expenses_breakdown.map(e => `
                    <tr style="background: #fafafa;">
                        <td style="padding-left: 24px; color: #475569;">• ${e.category_name}</td>
                        <td class="text-right" style="color: #dc2626;">- ₹${parseFloat(e.total_amount).toFixed(2)}</td>
                    </tr>
                `).join("");
            } else {
                expDetails = `
                    <tr style="background: #fafafa;">
                        <td style="padding-left: 24px; color: #64748b;">• No shop expenses recorded</td>
                        <td class="text-right">₹0.00</td>
                    </tr>
                `;
            }

            stmtTbody.innerHTML = `
                <tr>
                    <td><b>A. Revenue from Operations (Taxable Turnover)</b></td>
                    <td class="text-right" style="font-weight: 700;">₹${(data.sales_revenue || 0).toFixed(2)}</td>
                </tr>
                <tr>
                    <td style="color: #dc2626;"><b>Less: Cost of Goods Sold (COGS - Batch Cost)</b></td>
                    <td class="text-right" style="color: #dc2626; font-weight: 700;">- ₹${(data.cogs || 0).toFixed(2)}</td>
                </tr>
                <tr style="background: #f0fdf4; border-top: 2px solid #86efac; border-bottom: 2px solid #86efac;">
                    <td><b style="color: #047857;">GROSS PROFIT (A - COGS) [${data.gross_margin_pct}% Margin]</b></td>
                    <td class="text-right"><b style="color: #047857; font-size: 14px;">₹${(data.gross_profit || 0).toFixed(2)}</b></td>
                </tr>
                <tr>
                    <td colspan="2" style="font-weight: 700; color: #334155; padding-top: 10px;">B. Operating / Shop Expenses</td>
                </tr>
                ${expDetails}
                <tr style="background: ${npVal >= 0 ? '#faf5ff' : '#fef2f2'}; border-top: 2px solid #cbd5e1; border-bottom: 3px double #334155;">
                    <td><b style="font-size: 13.5px; color: ${npVal >= 0 ? '#7e22ce' : '#dc2626'};">NET OPERATING PROFIT (NP) [${data.net_margin_pct}%]</b></td>
                    <td class="text-right"><b style="font-size: 15px; color: ${npVal >= 0 ? '#7e22ce' : '#dc2626'};">₹${npVal.toFixed(2)}</b></td>
                </tr>
                <tr>
                    <td style="color: #64748b; font-size: 11px;">📦 Closing Stock Valuation (Inventory Asset at Shop)</td>
                    <td class="text-right" style="color: #64748b; font-size: 11px; font-weight: 600;">₹${(data.closing_stock_value || 0).toFixed(2)}</td>
                </tr>
            `;
        }

        // 4. Render Category Margin Breakdown
        const catTbody = document.getElementById("pnl-category-tbody");
        if (catTbody) {
            if (!data.category_breakdown || data.category_breakdown.length === 0) {
                catTbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted" style="padding: 20px;">No sales by category in this period.</td></tr>';
            } else {
                catTbody.innerHTML = data.category_breakdown.map(c => `
                    <tr>
                        <td><b>${c.category_name}</b></td>
                        <td class="text-right">₹${c.sales_revenue.toFixed(2)}</td>
                        <td class="text-right" style="color: #dc2626;">₹${c.cogs.toFixed(2)}</td>
                        <td class="text-right" style="font-weight: 700; color: #047857;">₹${c.gross_profit.toFixed(2)}</td>
                        <td class="text-center"><span class="badge ${c.margin_pct >= 15 ? 'badge-success' : 'badge-warning'}">${c.margin_pct}%</span></td>
                    </tr>
                `).join("");
            }
        }

        // 5. Fetch Product-Wise Profitability Breakdown
        const prodRes = await fetch(`/api/accounting/profit-and-loss/products?from_date=${fromDate}&to_date=${toDate}`);
        pnlAllProducts = await prodRes.json();
        filterPnLProducts();

    } catch (err) {
        console.error("Failed to load P&L:", err);
    }
}

function filterPnLProducts() {
    const search = document.getElementById("pnl-prod-search")?.value.trim().toLowerCase() || "";
    const tbody = document.getElementById("pnl-products-tbody");
    if (!tbody) return;

    let filtered = pnlAllProducts || [];
    if (search) {
        filtered = filtered.filter(p => 
            p.product_name.toLowerCase().includes(search) ||
            p.category_name.toLowerCase().includes(search) ||
            p.manufacturer_name.toLowerCase().includes(search)
        );
    }

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted" style="padding: 20px;">No product sales matching "${search}".</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => `
        <tr>
            <td><b>${p.product_name}</b></td>
            <td><span class="badge" style="background:#e0f2fe; color:#0369a1;">${p.category_name}</span></td>
            <td>${p.manufacturer_name}</td>
            <td class="text-center"><b>${p.qty_sold}</b> ${p.unit_symbol}</td>
            <td class="text-right">₹${p.sales_revenue.toFixed(2)}</td>
            <td class="text-right" style="color: #dc2626;">₹${p.cogs.toFixed(2)}</td>
            <td class="text-right" style="font-weight: 700; color: #047857;">₹${p.gross_profit.toFixed(2)}</td>
            <td class="text-center"><span class="badge ${p.margin_pct >= 15 ? 'badge-success' : 'badge-fefo'}">${p.margin_pct}%</span></td>
        </tr>
    `).join("");
}

// ============================================================
// SECURITY, AUTHENTICATION & ACCESS CONTROL
// ============================================================

async function checkAuthState() {
    const token = localStorage.getItem("krushidhan_auth_token");
    if (!token) {
        showLoginOverlay();
        return false;
    }

    try {
        const res = await _originalFetch("/api/auth/me", {
            headers: { "Authorization": `Bearer ${token}` }
        });

        if (res.ok) {
            const data = await res.json();
            currentUser = data.user;
            hideLoginOverlay();
            updateUserInterfaceForRole();
            return true;
        } else {
            showLoginOverlay("Session expired. Please log in again.");
            return false;
        }
    } catch (e) {
        console.error("Auth check failed:", e);
        showLoginOverlay();
        return false;
    }
}

function showLoginOverlay(errorMessage = "") {
    const overlay = document.getElementById("login-screen-overlay");
    if (overlay) {
        overlay.style.display = "flex";
    }
    const errBox = document.getElementById("login-error-box");
    if (errBox) {
        if (errorMessage) {
            errBox.textContent = errorMessage;
            errBox.style.display = "block";
        } else {
            errBox.style.display = "none";
        }
    }
    const usernameInput = document.getElementById("login-username");
    if (usernameInput) {
        setTimeout(() => usernameInput.focus(), 150);
    }
}

function hideLoginOverlay() {
    const overlay = document.getElementById("login-screen-overlay");
    if (overlay) {
        overlay.style.display = "none";
    }
}

async function submitLogin() {
    const usernameInput = document.getElementById("login-username");
    const passwordInput = document.getElementById("login-password");
    const btnSubmit = document.getElementById("btn-login-action");
    const errBox = document.getElementById("login-error-box");

    const username = usernameInput?.value.trim() || "";
    const password = passwordInput?.value || "";

    if (!username || !password) {
        if (errBox) {
            errBox.textContent = "कृपया User ID आणि Password दोन्ही टाका.";
            errBox.style.display = "block";
        }
        return;
    }

    if (btnSubmit) {
        btnSubmit.disabled = true;
        btnSubmit.textContent = "⏳ पडताळणी सुरू आहे...";
    }
    if (errBox) errBox.style.display = "none";

    try {
        const res = await _originalFetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await res.json();
        if (res.ok && data.success && data.token) {
            localStorage.setItem("krushidhan_auth_token", data.token);
            currentUser = data.user;
            hideLoginOverlay();
            updateUserInterfaceForRole();
            if (passwordInput) passwordInput.value = "";
            await bootstrapDashboard();
        } else {
            const msg = data.detail || "चुकीचा युझर आयडी किंवा पासवर्ड (Invalid User ID or Password)";
            if (errBox) {
                errBox.textContent = msg;
                errBox.style.display = "block";
            }
        }
    } catch (err) {
        console.error("Login request error:", err);
        if (errBox) {
            errBox.textContent = "सर्व्हरशी संपर्क होऊ शकला नाही. कृपया पुन्हा प्रयत्न करा.";
            errBox.style.display = "block";
        }
    } finally {
        if (btnSubmit) {
            btnSubmit.disabled = false;
            btnSubmit.textContent = "🔒 सुरक्षित प्रवेश करा (Secure Login)";
        }
    }
}

function handleLogout() {
    if (confirm("तुम्हाला नक्की लॉगआउट करायचे आहे का? (Do you want to log out?)")) {
        localStorage.removeItem("krushidhan_auth_token");
        currentUser = null;
        showLoginOverlay("यशस्वीरित्या लॉगआउट केले. (Logged out successfully)");
    }
}

function updateUserInterfaceForRole() {
    if (!currentUser) return;

    const nameEl = document.getElementById("user-display-name");
    const roleEl = document.getElementById("user-display-role");
    
    if (nameEl) nameEl.textContent = currentUser.full_name || currentUser.username;
    if (roleEl) {
        roleEl.textContent = currentUser.role || "OPERATOR";
        if (currentUser.role === "ADMIN") {
            roleEl.className = "user-role-tag role-admin";
        } else {
            roleEl.className = "user-role-tag role-operator";
        }
    }

    // Role Based Navigation Tabs and Elements
    const pnlTab = document.querySelector('.nav-tab[data-tab="tab-pnl"]');
    const settingsTab = document.querySelector('.nav-tab[data-tab="tab-settings"]');
    const userMgmtCard = document.getElementById("settings-user-mgmt-card");

    if (currentUser.role !== "ADMIN") {
        if (pnlTab) pnlTab.style.display = "none";
        if (userMgmtCard) userMgmtCard.style.display = "none";
    } else {
        if (pnlTab) pnlTab.style.display = "flex";
        if (userMgmtCard) userMgmtCard.style.display = "block";
    }
}

function togglePasswordVisibility(fieldId) {
    const input = document.getElementById(fieldId);
    if (!input) return;
    input.type = (input.type === "password") ? "text" : "password";
}

// ----------------- Change Password Modal -----------------
function openChangePasswordModal() {
    document.getElementById("modal-change-password").style.display = "flex";
    document.getElementById("pwd-old").value = "";
    document.getElementById("pwd-new").value = "";
    document.getElementById("pwd-confirm").value = "";
}

function closeChangePasswordModal() {
    document.getElementById("modal-change-password").style.display = "none";
}

async function submitChangePassword() {
    const oldPwd = document.getElementById("pwd-old").value;
    const newPwd = document.getElementById("pwd-new").value;
    const confirmPwd = document.getElementById("pwd-confirm").value;

    if (newPwd !== confirmPwd) {
        alert("नवीन पासवर्ड आणि पुष्टीकरण पासवर्ड जुळत नाहीत!");
        return;
    }

    try {
        const res = await fetch("/api/auth/change-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password: oldPwd, new_password: newPwd })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            alert("✓ " + (data.message || "पासवर्ड यशस्वीरीत्या बदलला आहे!"));
            closeChangePasswordModal();
        } else {
            alert("त्रुटी: " + (data.detail || "पासवर्ड बदलता आला नाही."));
        }
    } catch (e) {
        alert("पासवर्ड बदलताना त्रुटी आली: " + e.message);
    }
}

// ----------------- User Management (Admin Only) -----------------
async function loadAuthUsers() {
    if (!currentUser || currentUser.role !== "ADMIN") return;
    const tbody = document.getElementById("auth-users-tbody");
    if (!tbody) return;

    try {
        const res = await fetch("/api/auth/users");
        if (!res.ok) return;
        const users = await res.json();

        if (!users || users.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No users registered yet.</td></tr>';
            return;
        }

        tbody.innerHTML = users.map(u => `
            <tr>
                <td><b>#${u.user_id}</b></td>
                <td><b>${u.username}</b></td>
                <td>${u.full_name || "-"}</td>
                <td>
                    <span class="user-role-tag ${u.role === 'ADMIN' ? 'role-admin' : 'role-operator'}">${u.role}</span>
                </td>
                <td>
                    <span class="badge ${u.is_active ? 'badge-success' : 'badge-danger'}">${u.is_active ? 'सक्रिय (Active)' : 'निष्क्रिय (Disabled)'}</span>
                </td>
                <td class="text-center">
                    ${u.user_id !== currentUser.user_id ? `
                        <button class="btn btn-secondary btn-sm" onclick="toggleUserStatus(${u.user_id}, ${u.is_active})" style="padding: 3px 8px; font-size: 11px;">
                            ${u.is_active ? 'Disable' : 'Enable'}
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="adminResetPassword(${u.user_id}, '${u.username}')" style="padding: 3px 8px; font-size: 11px;">
                            🔑 Reset PIN
                        </button>
                    ` : '<span style="font-size:11px; color:#64748b;">(Current Account)</span>'}
                </td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Failed to load auth users:", e);
    }
}

function openCreateUserModal() {
    document.getElementById("modal-create-user").style.display = "flex";
    document.getElementById("new-user-username").value = "";
    document.getElementById("new-user-fullname").value = "";
    document.getElementById("new-user-password").value = "";
    document.getElementById("new-user-role").value = "OPERATOR";
}

function closeCreateUserModal() {
    document.getElementById("modal-create-user").style.display = "none";
}

async function submitCreateUser() {
    const username = document.getElementById("new-user-username").value.trim();
    const full_name = document.getElementById("new-user-fullname").value.trim();
    const password = document.getElementById("new-user-password").value;
    const role = document.getElementById("new-user-role").value;

    if (!username || !password || !full_name) {
        alert("सर्व माहिती भरणे आवश्यक आहे.");
        return;
    }

    try {
        const res = await fetch("/api/auth/users", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, full_name, role })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            alert(`✓ User '${username}' यशस्वीरीत्या तयार केला!`);
            closeCreateUserModal();
            loadAuthUsers();
        } else {
            alert("त्रुटी: " + (data.detail || "User तयार करता आला नाही."));
        }
    } catch (e) {
        alert("User तयार करताना त्रुटी आली: " + e.message);
    }
}

async function toggleUserStatus(userId, currentStatus) {
    const newStatus = !currentStatus;
    const actionName = newStatus ? "सक्रिय (Activate)" : "निष्क्रिय (Deactivate)";
    if (!confirm(`तुम्हाला या User ला ${actionName} करायचे आहे का?`)) return;

    try {
        const res = await fetch(`/api/auth/users/${userId}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_active: newStatus })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            loadAuthUsers();
        } else {
            alert(data.detail || "Status update failed");
        }
    } catch (e) {
        alert("त्रुटी: " + e.message);
    }
}

async function adminResetPassword(userId, username) {
    const newPwd = prompt(`'${username}' या युझरसाठी नवीन पासवर्ड टाका (Enter new password):`);
    if (!newPwd || newPwd.trim().length < 4) {
        if (newPwd !== null) alert("पासवर्ड किमान 4 अक्षरांचा असावा.");
        return;
    }

    try {
        const res = await fetch(`/api/auth/users/${userId}/reset-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ new_password: newPwd.trim() })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(`✓ '${username}' चा पासवर्ड बदलला आहे!`);
        } else {
            alert("त्रुटी: " + (data.detail || "Password reset failed"));
        }
    } catch (e) {
        alert("त्रुटी: " + e.message);
    }
}


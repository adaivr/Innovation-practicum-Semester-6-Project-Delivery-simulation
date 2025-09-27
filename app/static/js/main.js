// ------------------------
// Работа с сервером
// ------------------------
async function fetchJSON(url, options = {}) {
    const resp = await fetch(url, options);
    return await resp.json();
}

// -------------------------
// Создание сайта
// -------------------------
let cities = [];
let updating = false;
let currentDateCache = null;

async function getCities() {
    const data = await fetchJSON('/cities');
    return data.map(city => city.cityName);
}

async function main() {
    cities = await getCities();
    await updateDate(0);
    await Promise.all([updateMap(), updateTable()]);
}

async function updateAll(shift = 0) {
    if (updating) return;
    updating = true;
    
    await updateDate(shift);
    await Promise.all([updateMap(), updateTable()]);
    
    updating = false;
}

main();

// ------------------------
// Карта
// ------------------------
const map = L.map('map').setView([52, 49], 5);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 10
}).addTo(map);

let mapLayers = {
    routes: L.layerGroup().addTo(map),
    cities: L.layerGroup().addTo(map),
    orders: L.layerGroup().addTo(map)
};

async function getMapData() {
    return await fetchJSON('/map');
}

function clearMapLayers() {
    Object.values(mapLayers).forEach(layer => layer.clearLayers());
}

function drawMap(data) {
    clearMapLayers();

    // Маршруты
    data.routes.forEach(route => {
        L.polyline([route.routeFrom, route.routeTo], {
            color: '#10069f',
            weight: 4,
            opacity: 0.5
        }).addTo(mapLayers.routes);
    });

    // Города
    data.cities.forEach(city => {
        L.circleMarker([city.cityLat, city.cityLon], {
            radius: 8,
            fillColor: "#ff7500",
            color: "#ff7500",
            weight: 2,
            fillOpacity: 0.8
        })
            .addTo(mapLayers.cities)
            .bindTooltip(city.cityName, {
                direction: 'top',
                offset: [0, -5],
                className: 'custom-tooltip'
            });
    });

    // Заказы
    data.orders.forEach(order => {
        const lonSize = 0.3, latSize = 0.3;
        const triangle = [
            [order.orderLat, order.orderLon],
            [order.orderLat + latSize, order.orderLon - lonSize],
            [order.orderLat + latSize, order.orderLon + lonSize]
        ];
        L.polygon(triangle, {
            color: "#3cb371",
            weight: 2,
            fillColor: "#3cb371",
            fillOpacity: 0.8
        })
            .addTo(mapLayers.orders)
            .bindTooltip(
                `<b>Заказ №${order.orderId}</b><br>${order.fromName} - ${order.toName}`,
                { direction: 'top', offset: [0, -5], className: 'custom-tooltip' }
            );
    });
}

async function updateMap() {
    const data = await getMapData();
    drawMap(data);
}

// ------------------------
// Дата
// ------------------------
async function shiftDate(shift = 0) {
    if (shift === 0 && currentDateCache) {
        return currentDateCache;
    }
    
    const data = await fetchJSON('/date', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: shift })
    });
    
    currentDateCache = data.date;
    return data.date;
}

async function updateDate(shift = 0) {
    document.getElementById("currentDate").innerText = await shiftDate(shift);
}

// ------------------------
// Таблица заказов
// ------------------------

function createOptions(options, selected) {
    return [''].concat(options).map(opt => `
        <option value="${opt || ''}" ${String(opt) === String(selected) ? "selected" : ""}>
            ${opt || ""}
        </option>
    `).join("");
}

function createOrderRow(order, currentDateStr) {
    const [day, month, year] = currentDateStr.split('.').map(Number);
    const date = new Date(year, month - 1, day + 1);
    const minDate = date.toISOString().split('T')[0];
    
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td></td>
        <td><select class="fromName">${createOptions(cities, order.fromName)}</select></td>
        <td><select class="toName">${createOptions(cities, order.toName)}</select></td>
        <td><select class="orderClass">${createOptions(["Скорая", "Стандарт"], order.orderClass)}</select></td>
        <td><select class="weight">${createOptions([1, 2, 3, 4, 5], order.weight)}</select></td>
        <td><input type="date" class="startDate" value="${order.startDate || ''}" min="${minDate}"></td>
        <td></td>
        <td></td>
        <td></td>
        <td><button class="deleteBtn btn-order-delete">Удалить</button></td>
    `;

    const startDateInput = tr.querySelector(".startDate");
    startDateInput.addEventListener("keydown", e => e.preventDefault());
    startDateInput.addEventListener("change", e => {
        order.startDate = e.target.value || null;
        if (e.target.value < minDate) e.target.value = minDate;
    });

    tr.querySelector(".fromName").addEventListener("change", e => order.fromName = e.target.value || null);
    tr.querySelector(".toName").addEventListener("change", e => order.toName = e.target.value || null);
    tr.querySelector(".orderClass").addEventListener("change", e => order.orderClass = e.target.value || null);
    tr.querySelector(".weight").addEventListener("change", e => order.weight = e.target.value ? parseInt(e.target.value) : null);
    tr.querySelector(".deleteBtn").addEventListener("click", () => {
        orders = orders.filter(o => o !== order);
        updateTable();
    });

    return tr;
}

function createOldOrderRow(order) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td>${order.orderId}</td>
        <td>${order.fromName || ""}</td>
        <td>${order.toName || ""}</td>
        <td>${order.orderClass || ""}</td>
        <td>${order.weight || ""}</td>
        <td>${order.startDate || ""}</td>
        <td>${order.expectedDate || ""}</td>
        <td>${order.orderStatus || ""}</td>
        <td>${order.delay || ""}</td>
        <td></td>
    `;
    return tr;
}

async function updateTable() {
    const tbody = document.querySelector("#ordersTable tbody");
    const currentDateStr = await shiftDate();
    
    const [oldOrdersData, newRowsFragment] = await Promise.all([
        fetchJSON('/orders'),
        (async () => {
            const fragment = document.createDocumentFragment();
            for (const order of orders) {
                fragment.appendChild(createOrderRow(order, currentDateStr));
            }
            return fragment;
        })()
    ]);

    tbody.innerHTML = "";
    tbody.appendChild(newRowsFragment);
    
    oldOrdersData.forEach(order => {
        tbody.appendChild(createOldOrderRow(order));
    });
}

// -------------------------
// Симуляция
// -------------------------
let orders = [];
let simulationActive = false;
let simulationRunning = false;

async function sendOrders() {
    const newOrders = orders.filter(o =>
        o.fromName &&
        o.toName &&
        o.orderClass &&
        o.weight &&
        o.startDate
    );
    
    orders = [];
    
    if (newOrders.length === 0) return;
    
    await fetchJSON('/send', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newOrders)
    });
}

async function runSimulation() {
    if (simulationRunning) return;
    simulationRunning = true;

    while (simulationActive) {
        await updateAll(1);
        await new Promise(r => setTimeout(r, 50));
    }

    simulationRunning = false;
}

async function invertSimulation() {
    simulationActive = !simulationActive;
    if (simulationActive) {
        simulationBtn.innerText = "Остановить симуляцию";
        simulationBtn.classList.replace("btn-blue", "btn-orange");
        await sendOrders();
        runSimulation();
    } else {
        simulationBtn.innerText = "Запустить симуляцию";
        simulationBtn.classList.replace("btn-orange", "btn-blue");
    }
}

async function stopSimulation() {
    if (simulationActive) {
        await invertSimulation();
    }
}

// -------------------------
// Кнопки
// -------------------------
const simulationBtn = document.getElementById("simulationBtn");
const prevDateBtn = document.getElementById("prevDateBtn");
const nextDateBtn = document.getElementById("nextDateBtn");
const addOrderBtn = document.getElementById("addOrderBtn");
const deleteAllOrdersBtn = document.getElementById("deleteAllOrdersBtn");

async function handlePlayPause() {
    await invertSimulation();
    await updateAll();
}

async function prevDate() {
    await stopSimulation();
    await updateAll(-1);
}

async function nextDate() {
    await stopSimulation();
    await sendOrders();
    await updateAll(1);
}

async function addOrder() {
    await stopSimulation();
    orders.unshift({
        fromName: null,
        toName: null,
        orderClass: null,
        weight: null,
        startDate: null,
    });
    await updateTable();
}

async function deleteAllOrders() {
    await stopSimulation();
    await fetchJSON('/delete', { method: "POST" });
    orders = [];
    await updateAll();
}

simulationBtn.addEventListener("click", handlePlayPause);
prevDateBtn.addEventListener("click", prevDate);
nextDateBtn.addEventListener("click", nextDate);
addOrderBtn.addEventListener("click", addOrder);
deleteAllOrdersBtn.addEventListener("click", deleteAllOrders);
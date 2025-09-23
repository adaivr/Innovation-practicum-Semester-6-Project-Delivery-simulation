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

async function getCities() {
    return await fetchJSON('/cities');
}

async function main() {
    cities = await getCities();
    await updateMap();
    await updateDate();
    await updateTable();
}

async function updateAll(shift = 0) {
    await updateDate(shift);
    await updateMap();
    await updateTable();
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

async function getMapData() {
    return await fetchJSON('/map');
}

function clearMapLayers() {
    map.eachLayer(layer => {
        if (
            layer instanceof L.Polyline ||
            layer instanceof L.CircleMarker ||
            layer instanceof L.Rectangle
        ) {
            map.removeLayer(layer);
        }
    });
}

function drawMap(data) {
    clearMapLayers();

    // Маршруты
    data.routes.forEach(route => {
        L.polyline([route.routeFrom, route.routeTo], {
            color: '#10069f',
            weight: 4,
            opacity: 0.5
        }).addTo(map);
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
            .addTo(map)
            .bindTooltip(city.cityName, {
                direction: 'top',
                offset: [0, -5],
                className: 'custom-tooltip'
            });
    });

    // Заказы
    data.orders.forEach(order => {
        const lonSize = 0.2, latSize = 0.12;
        const bounds = [
            [order.orderLat - latSize, order.orderLon - lonSize],
            [order.orderLat + latSize, order.orderLon + lonSize]
        ];
        L.rectangle(bounds, {
            color: "#3cb371",
            weight: 2,
            fillColor: "#3cb371",
            fillOpacity: 0.8
        })
            .addTo(map)
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
    const data = await fetchJSON('/date', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: shift })
    });
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

async function createOrderRow(order) {
    const str = await shiftDate();
    const [day, month, year] = str.split('.').map(Number);
    const date = new Date(year, month - 1, day);
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td></td>
        <td><select class="fromName">${createOptions(cities.map(c => c), order.fromName)}</select></td>
        <td><select class="toName">${createOptions(cities.map(c => c), order.toName)}</select></td>
        <td><select class="orderClass">${createOptions(["Скорая", "Стандарт"], order.orderClass)}</select></td>
        <td><select class="weight">${createOptions([5, 10, 50, 100], order.weight)}</select></td>
        <td><input type="date" class="startDate" value="${order.startDate || ''}" min="${date.toISOString().split('T')[0]}"></td>
        <td></td>
        <td></td>
        <td></td>
        <td><button class="deleteBtn btn-order-delete">Удалить</button></td>
    `;

    const startDateInput = tr.querySelector(".startDate");
    startDateInput.addEventListener("keydown", e => e.preventDefault());
    startDateInput.addEventListener("change", e => {
        order.startDate = e.target.value || null;
        if (e.target.value < date) e.target.value = date;
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
        <td>${order.id}</td>
        <td>${order.fromName || ""}</td>
        <td>${order.toName || ""}</td>
        <td>${order.orderClass || ""}</td>
        <td>${order.weight || ""}</td>
        <td>${order.startDate || ""}</td>
        <td>${order.expectedDate || ""}</td>
        <td>${order.status || ""}</td>
        <td>${order.delay || ""}</td>
        <td></td>
    `;
    return tr;
}

async function updateTable() {
    const tbody = document.querySelector("#ordersTable tbody");
    tbody.innerHTML = "";

    for (const order of orders) {
        tbody.appendChild(await createOrderRow(order));
    }

    const oldOrders = await fetchJSON('/orders');
    oldOrders.forEach(order => {
        tbody.appendChild(createOldOrderRow(order));
    });
}

// -------------------------
// Симуляция
// -------------------------
let orders = [];
let simulationActive = false;

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

async function simulationStep() {
    await fetchJSON('/step');
    await updateAll(1);
}

async function runSimulation() {
    if (!simulationActive) return;
    await simulationStep();
    setTimeout(runSimulation, 100);
}

async function invertSimulation() {
    simulationActive = !simulationActive;
    if (simulationActive) {
        simulationBtn.innerText = "Остановить симуляцию";
        simulationBtn.classList.replace("btn-blue", "btn-orange");
        await sendOrders();
        await runSimulation();
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
    await simulationStep();
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
    await updateAll();
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

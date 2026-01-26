class GameWS {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.handlers = new Map(); // 存储不同业务的处理器
        this.setup();
    }

    // --- 统一的发送方法 ---
    send(type, subType, payload = {}) {
        const message = JSON.stringify({
            type: type,
            sub_type: subType,
            data: payload,
            timestamp: Date.now()
        });
        console.log("GameWSocket.send: ", message)
        this.socket.send(message);
    }

    // --- 统一的业务注册方法 ---
    // 允许不同的业务模块“挂载”到这个连接上 。 收到信息时候回调callback
    subscribe(type, callback) {
        this.handlers.set(type, callback);
        console.log("subscribe. ", type, callback)
    }

    // --- 统一的底层监听 ---
    setup() {
        console.log(this.url)
        this.socket = new WebSocket(this.url);

        this.socket.onmessage = (e) => {
            const msg = JSON.parse(e.data);
            // 统一路由：根据 type 找到对应的业务回调
            const handler = this.handlers.get(msg.type);
            console.log("onmessage: ", msg, handler)
            if (handler) handler(msg);
        };

        this.socket.onclose = () => {
            console.log("连接断开，触发统一重连...");
            setTimeout(() => this.setup(), 5000);
        };
    }
}

function parseJwt(token) {
    try {
        // 获取中间的 Payload 部分
        const base64Url = token.split('.')[1];
        // 将 Base64Url 转换为标准的 Base64
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        // 解码并解析为 JSON
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function (c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        return JSON.parse(jsonPayload);
    } catch (e) {
        console.error("JWT 解析失败", e);
        return null;
    }
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

function getUserInfo() {
    return JSON.parse(atob(getCookie("user_info")));
}

/**
 * 秒数 可读字符串
 * @param remainingSec
 * @returns {string}
 */
function formatTime(remainingSec) {
    if (remainingSec <= 0) return "00:00:00";

    const hours = Math.floor(remainingSec / 3600);
    const minutes = Math.floor((remainingSec % 3600) / 60);
    const seconds = remainingSec % 60;

    // 使用 padStart 补零，确保格式为 HH:mm:ss
    const h = String(hours).padStart(2, '0');
    const m = String(minutes).padStart(2, '0');
    const s = String(seconds).padStart(2, '0');

    return `${h}:${m}:${s}`;
}


/**
 * 计算任务进度百分比
 * @param {string} startTimeStr - "2026-01-22T10:05:21.375000"
 * @param {string} endTimeStr - "2026-01-22T11:05:21.375000"
 * @returns {number} 0-100 之间的数值
 */
function calculateProgress(startTimeStr, endTimeStr) {
    const start = new Date(startTimeStr).getTime();
    const end = new Date(endTimeStr).getTime();
    const now = new Date().getTime(); // 获取当前时间 (2026-01-22 ...)

    // 如果当前时间还没到开始时间
    if (now < start) return 0;

    // 如果当前时间已经超过结束时间
    if (now > end) return 100;

    // 计算百分比
    const totalDuration = end - start;
    const elapsed = now - start;
    const progress = (elapsed / totalDuration) * 100;

    return Math.floor(progress); // 取整，或者使用 .toFixed(2) 保留两位小数
}

/**
 *  图标渲染函数
 * @param {string} iconName - 图标类名或标识符
 * @param {string} defaultIcon - 缺省时显示的 Emoji 或类名
 * @returns {string} - 完整的 HTML 字符串
 */
function renderIcon(iconName, defaultIcon = '🏗️') {
    // 如果没有传入 iconName，直接返回默认值
    if (!iconName || iconName.trim() === "") {
        return `<span>${defaultIcon}</span>`;
    }

    // 如果 iconName 看起来像类名（不包含 HTML 标签），则封装成 <i>
    // 逻辑：如果 iconName 里有 'bi-' 或 'fa-'，判定为图标库类名
    if (iconName.includes('bi-') || iconName.includes('fa-')) {
        return `<i class="${iconName} me-2"></i>`;
    }

    // 否则，它可能本身就是一个 Emoji
    return `<span class="me-2">${iconName}</span>`;
}

// 通用 Toast 显示函数
function showToast(message, type = 'success') {
    const toastEl = document.getElementById('liveToast');
    const toastMessage = document.getElementById('toastMessage');
    const toastTitle = document.getElementById('toastTitle');

    // 设置颜色主题
    toastEl.classList.remove('bg-success', 'bg-danger', 'text-white');
    if (type === 'success') {
        toastEl.classList.add('bg-success', 'text-white');
        toastTitle.innerText = '成功';
    } else {
        toastEl.classList.add('bg-danger', 'text-white');
        toastTitle.innerText = '错误';
    }

    toastMessage.innerText = message;

    const toast = new bootstrap.Toast(toastEl);
    toast.show();
}

function formatValue(value) {
    if (value >= 100000000) {
        return (value / 100000000).toFixed(2) + ' 亿';
    } else if (value >= 10000) {
        return (value / 10000).toFixed(2) + ' 万';
    }
    return value.toLocaleString(); // 加上逗号分隔
}

const gameWS = new GameWS(`ws://${window.location.host}/ws/${getUserInfo().name}`);

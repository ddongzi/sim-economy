class GameWS {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.handlers = new Map(); // 存储不同业务的处理器
        this.setup();
    }

    // --- 统一的发送方法 ---
    send(type, sub_type, payload = {}) {
        const message = JSON.stringify({
            type: type,
            sub_type: sub_type,
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
function formatGameTime(isoTime) {
    const diff = (new Date() - new Date(isoTime)) / 1000; // 秒数差

    if (diff < 60) return "刚刚";
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    return "远方的信件";
}
/**
 * 秒数 可读字符串
 * @param remainingSec
 * @returns {string}
 */
function formatRemainSec(remainingSec) {
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

function formatTime(timeStr) {
    const date = new Date(timeStr);

// 转换为：2026/1/20 08:17:45 (假设你在北京时区)
    return  date.toLocaleString();

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

/**
 * 金钱
 * @param value
 * @returns {string}
 */
function formatCashValue(value) {
    if (value >= 100000000) {
        return (value / 100000000).toFixed(2) + ' 亿';
    } else if (value >= 10000) {
        return (value / 10000).toFixed(2) + ' 万';
    }
    return value.toLocaleString(); // 加上逗号分隔
}

function formatQuantity(val) {
    if (val >= 1000000) return (val / 1000000).toFixed(1) + 'M';
    if (val >= 1000) return (val / 1000).toFixed(1) + 'K';
    return val.toString(); // 数量较小时不加逗号，保持紧凑
}

/**
 * 通用指标更新器
 * @param {string} idPrefix  HTML元素ID的前缀 (如 'gini', 'm0')
 * @param {number} current   当前值
 * @param {number} total     总值 (用于计算进度条百分比，若本身就是百分比则传1)
 * @param {number} precision 保留小数位数
 */
function updateMetric(idPrefix, current, total, precision = 2) {
    const ratio = total === 0 ? 0 : current / total;
    const percentage = (Math.min(ratio, 1) * 100).toFixed(1) + '%';

    // 1. 更新数值文字
    const valElem = document.getElementById(`${idPrefix}-val`);
    if (valElem) {
        valElem.innerText = current.toLocaleString(undefined, {
            minimumFractionDigits: precision,
            maximumFractionDigits: precision
        });
    }

    // 2. 更新进度条宽度
    const barElem = document.getElementById(`${idPrefix}-bar`);
    if (barElem) {
        barElem.style.width = percentage;

        // 3. 可选：根据阈值自动切换颜色 (以基尼指数或流动性为例)
        if (idPrefix === 'gini') {
            barElem.className = 'progress-bar ' + (ratio > 0.6 ? 'bg-danger' : ratio > 0.4 ? 'bg-warning' : 'bg-success');
        }
        if (idPrefix === 'm0') {
            // M0占比过低意味着流动性危机，变红预警
            barElem.className = 'progress-bar ' + (ratio < 0.2 ? 'bg-danger' : 'bg-primary');
        }
    }
}

// 定义一个全局 Promise，让其他脚本可以等待
const gameVersion = localStorage.getItem('gameVersion');
window.gameDataPromise = (async function () {
    try {
        // 1. 尝试读取本地缓存（同步，极快）
        const localDataRaw = localStorage.getItem("gameData");
        let localData = localDataRaw ? JSON.parse(localDataRaw) : null;

        // 2. 发起网络请求（并行处理）
        const res = await fetch("/api/gamedata", {
            headers: { 'If-None-Match': `${gameVersion}` }
        });
        if (res.status === 304) {
            console.log("gamedata 版本一致， 无需更新");
        } else {
            const serverData = await res.json();
            // 3. 版本比对
            if (!localData || localData.version !== serverData.version) {
                console.log("[数据同步] 更新缓存");
                localStorage.setItem("gameData", JSON.stringify(serverData));
                localStorage.setItem("gameVersion", serverData.version);
                localData = serverData;
            }
        }

        // 4. 挂载到 window
        window.gameData = localData;
        return localData;
    } catch (err) {
        console.error("[数据同步] 错误:", err);
        // 兜底策略：如果网络挂了，尝试用旧缓存
        if (window.gameData) return window.gameData;
        throw err;
    }
})(); // 立即执行


const gameWS = new GameWS(`ws://${window.location.host}/ws/${getUserInfo().name}`);

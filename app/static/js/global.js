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
    // 转化为 ISO 字符串，截取时间部分
    return new Date(remainingSec * 1000).toISOString().substring(11, 19);
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

const gameWS = new GameWS(`ws://${window.location.host}/ws/${getUserInfo().name}`);

const API = window.location.origin;

// Telegram WebApp
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.ready();
    tg.expand();
}

let telegramId = "";
let username = "Guest";

// Read Telegram user if available
if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
    telegramId = String(tg.initDataUnsafe.user.id);
    username = tg.initDataUnsafe.user.first_name || "Player";
} else {
    // Temporary for browser testing
    telegramId = "123456789";
    username = "Test Player";
}

document.getElementById("username").innerText = username;

async function loadUser() {
    try {
        const res = await fetch(API + "/api/users/" + telegramId);
        const user = await res.json();

        document.getElementById("username").innerText =
            user.first_name;

        document.getElementById("balance").innerText =
            user.balance + " ETB";
    } catch (e) {
        console.log(e);
    }
}

async function loadGame() {
    try {
        const res = await fetch(API + "/api/games/current");
        const game = await res.json();

        document.getElementById("gameStatus").innerText =
            game.status || "Waiting...";
    } catch (e) {
        document.getElementById("gameStatus").innerText =
            "Server Offline";
    }
}

document.getElementById("pickBtn").onclick = () => {
    alert("Pick Card page will be connected next.");
};

document.getElementById("depositBtn").onclick = () => {
    alert("Deposit feature coming next.");
};

document.getElementById("withdrawBtn").onclick = () => {
    alert("Withdraw feature coming next.");
};

loadUser();
loadGame();

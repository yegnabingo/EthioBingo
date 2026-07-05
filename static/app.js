// የቴሌግራም ዌብ አፕ መረጃን መውሰድ
const tg = window.Telegram ? window.Telegram.WebApp : null;
let telegramId = "123456789"; // ፎልባክ (ዲሞ) አይዲ
let username = "Guest Player";

if (tg) {
    tg.ready();
    tg.expand(); // ስክሪኑን ሙሉ ያደርገዋል
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        telegramId = tg.initDataUnsafe.user.id.toString();
        username = tg.initDataUnsafe.user.username || tg.initDataUnsafe.user.first_name || "Telegram User";
    }
}

// ኤለመንቶችን በስም ማውጣት
const timerText = document.getElementById("timer");
const usernameEl = document.getElementById("username");
const balanceEl = document.getElementById("balance");
const grid = document.getElementById("cardGrid");
const confirmBtn = document.getElementById("confirmBtn");

// የተጫዋች መረጃን ስክሪን ላይ መጻፍ (Loading... ን ያጠፋዋል)
if (usernameEl) usernameEl.innerText = username;
if (balanceEl) balanceEl.innerText = "0 ETB";

let seconds = 30;
let selectedCard = null;
let pickedCount = 0;

// ----------------------------
// 1-200 ካርዶችን መፍጠር
// ----------------------------
if (grid) {
    for (let i = 1; i <= 200; i++) {
        const card = document.createElement("div");
        card.className = "card-number";
        card.innerText = i;
        card.dataset.number = i;

        card.onclick = () => {
            if (card.classList.contains("taken")) return;

            document.querySelectorAll(".card-number.selected")
                .forEach(c => c.classList.remove("selected"));

            selectedCard = i;
            card.classList.add("selected");
        };
        grid.appendChild(card);
    }
}

// ----------------------------
// Confirm Button
// ----------------------------
if (confirmBtn) {
    confirmBtn.onclick = async () => {
        if (selectedCard == null) {
            alert("Select one card first.");
            return;
        }
        if (pickedCount >= 5) {
            alert("Maximum 5 cards reached.");
            return;
        }

        try {
            const response = await fetch("/api/cards/pick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    telegram_id: telegramId,
                    card_number: selectedCard
                })
            });

            const result = await response.json();

            if (result.success) {
                pickedCount++;
                const cardEl = document.querySelector(`[data-number="${selectedCard}"]`);
                if (cardEl) {
                    cardEl.classList.remove("selected");
                    cardEl.classList.add("taken");
                }
                alert(`Card ${selectedCard} reserved (${pickedCount}/5)`);
                selectedCard = null;
            } else {
                alert(result.message);
            }
        } catch (error) {
            console.error("Error:", error);
            alert("ਸርቨር ስህተት! እባክዎ እንደገና ይሞክሩ።");
        }
    };
}

// ----------------------------
// ⏱ የሰዓት ቆጣሪ (Timer)
// ----------------------------
const timer = setInterval(() => {
    seconds--;
    if (timerText) timerText.innerText = seconds;

    if (seconds <= 0) {
        clearInterval(timer);
        if (confirmBtn) confirmBtn.disabled = true;

        // ስክሪን መቀያየር (ከPick ወደ Draw ሰሌዳ)
        if (document.getElementById("pickSection")) document.getElementById("pickSection").style.display = "none";
        if (document.getElementById("drawBoard")) document.getElementById("drawBoard").style.display = "block";

        renderPlayerCard(demoCard);
    }
}, 1000);

// ----------------------------
// ቢንጎ ሰሌዳ (1-75)
// ----------------------------
const numberBoard = document.getElementById("numberBoard");
if (numberBoard) {
    for (let n = 1; n <= 75; n++) {
        const ball = document.createElement("div");
        ball.className = "ball";
        ball.id = "ball-" + n;
        ball.innerText = n;
        numberBoard.appendChild(ball);
    }
}

// ----------------------------
// WebSocket
// ----------------------------
const protocol = location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(protocol + "://" + location.host + "/ws");
let callCount = 0;

socket.onmessage = function (event) {
    try {
        const data = JSON.parse(event.data);
        if (data.type !== "ball") return;

        callCount++;
        if (document.getElementById("callCount")) document.getElementById("callCount").innerText = callCount;

        const ballEl = document.getElementById("ball-" + data.number);
        if (ballEl) ballEl.classList.add("called");
    } catch (e) {
        console.error("WebSocket Error:", e);
    }
};

// ----------------------------
// የቢንጎ ካርድ አሳዪ (Render)
// ----------------------------
function renderPlayerCard(card) {
    const board = document.getElementById("playerCard");
    if (!board) return;
    board.innerHTML = "";

    card.forEach(row => {
        row.forEach(value => {
            const cell = document.createElement("div");
            cell.className = "cell";
            if (value === "FREE") {
                cell.classList.add("free");
                cell.innerHTML = "★";
            } else {
                cell.innerHTML = value;
            }
            board.appendChild(cell);
        });
    });
}

const demoCard = [
    [4, 25, 37, 51, 61],
    [7, 16, 35, 60, 72],
    [5, 20, "FREE", 57, 73],
    [14, 17, 39, 48, 75],
    [3, 24, 45, 50, 71]
];

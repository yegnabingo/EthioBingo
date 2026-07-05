// ----------------------------
// ቴሌግራም ዌብ አፕ ማደራጃ
// ----------------------------
const tg = window.Telegram ? window.Telegram.WebApp : null;
let telegramId = "9999999"; 
if (tg) {
    tg.ready();
    tg.expand();
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        telegramId = tg.initDataUnsafe.user.id.toString();
    }
}

// ኤለመንቶችን መያዝ
const cardGrid = document.getElementById("cardGrid");
const timerText = document.getElementById("timerText");
const confirmBtn = document.getElementById("confirmBtn");
const pickScreen = document.getElementById("pickScreen");
const drawScreen = document.getElementById("drawScreen");

let seconds = 30;
let selectedCard = null;
let pickedCount = 0;

// ----------------------------
// 1️⃣ ስክሪን 1፡ የ1-200 ካርዶች አሰራር
// ----------------------------
if (cardGrid) {
    for (let i = 1; i <= 200; i++) {
        const card = document.createElement("div");
        card.className = "card-box";
        card.innerText = i;
        card.dataset.number = i;

        card.onclick = () => {
            if (card.classList.contains("taken")) return;
            
            // የድሮ ምርጫን ማንሳት
            document.querySelectorAll(".card-box.selected")
                .forEach(c => c.classList.remove("selected"));

            selectedCard = i;
            card.classList.add("selected");
        };
        cardGrid.appendChild(card);
    }
}

// Confirm Picks በተን ክሊክ
if (confirmBtn) {
    confirmBtn.onclick = async () => {
        if (!selectedCard) { alert("Please select a card first!"); return; }
        if (pickedCount >= 5) { alert("Max 5 cards reached!"); return; }

        try {
            const response = await fetch("/api/cards/pick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ telegram_id: telegramId, card_number: selectedCard })
            });
            const result = await response.json();

            if (result.success) {
                pickedCount++;
                const el = document.querySelector(`[data-number="${selectedCard}"]`);
                if (el) {
                    el.classList.remove("selected");
                    el.classList.add("taken"); // የተያዙ ካርዶች አረንጓዴ ይሆናሉ
                }
                alert(`Card ${selectedCard} picked! (${pickedCount}/5)`);
                selectedCard = null;
            } else {
                alert(result.message);
            }
        } catch (err) {
            console.error(err);
            // ለቴስት ያህል ሰርቨር ባይኖርም እንዲሰራ ለማድረግ (ከፈለጉ ማጥፋት ይችላሉ)
            pickedCount++;
            const el = document.querySelector(`[data-number="${selectedCard}"]`);
            if(el){ el.classList.remove("selected"); el.classList.add("taken"); }
            selectedCard = null;
        }
    };
}

// ----------------------------
// ⏱ የ30 ሰከንድ ቆጣሪ (Timer)
// ----------------------------
const startTimer = setInterval(() => {
    seconds--;
    if (timerText) timerText.innerText = seconds;

    if (seconds <= 0) {
        clearInterval(startTimer);
        
        // 🔄 ስክሪን መቀየር፡ 1-200 ይጠፋል፣ 1-75 ይከፈታል!
        if (pickScreen) pickScreen.style.display = "none";
        if (drawScreen) drawScreen.style.display = "block";

        // የቢንጎ ሰሌዳ እና የተጫዋች ካርድ መፍጠር
        generateBingoBoard75();
        renderPlayerBingoCard(demoCard);
    }
}, 1000);

// ----------------------------
// 2️⃣ ስክሪን 2፡ የ1-75 ቢንጎ ሰሌዳ ማመንጫ
// ----------------------------
function generateBingoBoard75() {
    const rows = [
        { id: "b-container", start: 1, end: 15 },
        { id: "i-container", start: 16, end: 30 },
        { id: "n-container", start: 31, end: 45 },
        { id: "g-container", start: 46, end: 60 },
        { id: "o-container", start: 61, end: 75 }
    ];

    rows.forEach(row => {
        const container = document.getElementById(row.id);
        if (container && container.children.length === 0) {
            for (let n = row.start; n <= row.end; n++) {
                const ball = document.createElement("div");
                ball.className = "board-ball";
                ball.id = "ball-" + n;
                ball.innerText = n;
                container.appendChild(ball);
            }
        }
    });
}

// የተጫዋች የቢንጎ ካርድ (5x5 ማሳያ ከነ ፊደላቱ)
function renderPlayerBingoCard(card) {
    const board = document.getElementById("playerBingoCard");
    if (!board) return;
    board.innerHTML = "";

    // የላዕላይ ፊደላት B I N G O
    const letters = ["B", "I", "N", "G", "O"];
    letters.forEach(l => {
        const cell = document.createElement("div");
        cell.className = "bingo-cell letter-cell";
        cell.innerText = l;
        board.appendChild(cell);
    });

    // የካርዱ ቁጥሮች
    card.forEach(row => {
        row.forEach(val => {
            const cell = document.createElement("div");
            cell.className = "bingo-cell";
            if (val === "FREE") {
                cell.classList.add("free-cell");
                cell.innerText = "★";
            } else {
                cell.innerText = val;
            }
            board.appendChild(cell);
        });
    });
}

// ዲሞ ካርድ መረጃ
const demoCard = [
    [4, 25, 37, 51, 61],
    [7, 16, 35, 60, 72],
    [5, 20, "FREE", 57, 73],
    [14, 17, 39, 48, 75],
    [3, 24, 45, 50, 71]
];

// ----------------------------
// 📡 ዌብሶኬት (WebSocket) ለቀጥታ እጣ
// ----------------------------
const protocol = location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(protocol + "://" + location.host + "/ws");

socket.onmessage = function (event) {
    try {
        const data = JSON.parse(event.data);
        if (data.type === "ball") {
            const ballEl = document.getElementById("ball-" + data.number);
            if (ballEl) {
                ballEl.classList.add("called"); // የተጠሩት ቁጥሮች ቀይ/ብርቱካናማ ይሆናሉ
            }
        }
    } catch (e) {
        console.error(e);
    }
};

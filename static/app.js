const tg = window.Telegram ? window.Telegram.WebApp : null;
let telegramId = "123456789"; 
if (tg?.initDataUnsafe?.user) {
    telegramId = tg.initDataUnsafe.user.id.toString();
}

const pickScreen = document.getElementById("pickScreen");
const drawScreen = document.getElementById("drawScreen");
const cardGrid = document.getElementById("cardGrid");
const timerText = document.getElementById("timerText");
const confirmBtn = document.getElementById("confirmBtn");
const playerBingoCardContainer = document.getElementById("playerBingoCard");
const callCountEl = document.getElementById("callCount");

let selectedCard = null;
let myPickedCards = [];

// 1️⃣ ካርዶችን ከሰርቨር አምጥቶ መሳል
async function loadAvailableCards() {
    if (!cardGrid) return;
    cardGrid.innerHTML = "";
    try {
        const response = await fetch("/api/cards/status");
        const takenCards = await response.json();

        for (let i = 1; i <= 200; i++) {
            const card = document.createElement("div");
            card.className = "card-box";
            card.innerText = i;
            card.dataset.number = i;

            if (takenCards.includes(i)) {
                card.classList.add("taken");
            } else {
                card.onclick = () => {
                    document.querySelectorAll(".card-box.selected").forEach(c => c.classList.remove("selected"));
                    selectedCard = i;
                    card.classList.add("selected");
                };
            }
            cardGrid.appendChild(card);
        }
    } catch (err) { console.error(err); }
}

// ካርድ ማረጋገጫ (Locking)
if (confirmBtn) {
    confirmBtn.onclick = async () => {
        if (!selectedCard) return alert("መጀመሪያ ካርድ ይምረጡ!");
        try {
            const response = await fetch("/api/cards/pick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ telegram_id: telegramId, card_number: selectedCard })
            });
            const result = await response.json();
            if (result.success) {
                myPickedCards.push(selectedCard);
                const el = document.querySelector(`[data-number="${selectedCard}"]`);
                if (el) { el.classList.remove("selected"); el.classList.add("taken"); }
                selectedCard = null;
            } else { alert(result.message); }
        } catch (err) { console.error(err); }
    };
}

// 2️⃣ ወደ DRAW SCREEN መቀየር
async function switchToDrawScreen() {
    if (pickScreen) pickScreen.style.display = "none";
    if (drawScreen) drawScreen.style.display = "block";
    generateBingoBoard75();
    if (myPickedCards.length > 0) {
        await fetchAndRenderPlayerCards();
    } else {
        playerBingoCardContainer.innerHTML = "<p style='color:grey;padding:20px;'>ያልተሳተፉበት እጣ እየተካሄደ ነው...</p>";
    }
}

function generateBingoBoard75() {
    const rows = ["b", "i", "n", "g", "o"];
    const ranges = [{s:1,e:15},{s:16,e:30},{s:31,e:45},{s:46,e:60},{s:61,e:75}];
    ranges.forEach((r, idx) => {
        const container = document.getElementById(`${rows[idx]}-container`);
        if (container && container.children.length === 0) {
            for (let n = r.s; n <= r.e; n++) {
                const ball = document.createElement("div");
                ball.className = "board-ball";
                ball.id = "ball-" + n;
                ball.innerText = n;
                container.appendChild(ball);
            }
        }
    });
}

async function fetchAndRenderPlayerCards() {
    if (!playerBingoCardContainer) return;
    playerBingoCardContainer.innerHTML = "";
    try {
        const response = await fetch(`/api/cards/get_matrix?card_number=${myPickedCards[0]}`);
        const data = await response.json();
        if (data?.matrix) {
            const letters = ["B", "I", "N", "G", "O"];
            letters.forEach(l => {
                const cell = document.createElement("div");
                cell.className = "bingo-cell letter-cell";
                cell.innerText = l;
                playerBingoCardContainer.appendChild(cell);
            });
            data.matrix.forEach(row => {
                row.forEach(val => {
                    const cell = document.createElement("div");
                    cell.className = "bingo-cell";
                    cell.dataset.value = val;
                    if (val === "FREE") {
                        cell.classList.add("free-cell", "marked");
                        cell.innerText = "★";
                    } else { cell.innerText = val; }
                    playerBingoCardContainer.appendChild(cell);
                });
            });
        }
    } catch (err) { console.error(err); }
}

// 📡 3️⃣ WEB ARRAY / WEBSOCKET ማመሳሰያ
const protocol = location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(protocol + "://" + location.host + "/ws");

socket.onmessage = function (event) {
    const data = JSON.parse(event.data);
    
    if (data.type === "time_update") {
        if (timerText) timerText.innerText = data.time;
    }
    
    if (data.type === "phase_change" && data.phase === "DRAW") {
        switchToDrawScreen();
    }
    
    if (data.type === "ball") {
        if (callCountEl) callCountEl.innerText = data.call_count;
        const ballEl = document.getElementById("ball-" + data.number);
        if (ballEl) ballEl.classList.add("called");
        
        // 🟢 AUTO MARKING
        document.querySelectorAll(`.bingo-cell[data-value="${data.number}"]`).forEach(cell => {
            cell.classList.add("marked");
        });
        
        // የቅርብ ኳሶች ማሳያ
        const recent = document.querySelectorAll(".recent-ball");
        if(recent.length > 0) {
            for (let i = recent.length - 1; i > 0; i--) { recent[i].innerText = recent[i-1].innerText; }
            recent[0].innerText = data.number;
        }
    }
    
    if (data.type === "game_over") {
        alert(`🎉 ቢንጎ! ካርድ ቁጥር #${data.winner_card} አሸንፏል!\n💰 ሽልማት: ${data.prize} ETB (20% ኮሚሽን ተቀንሷል)`);
        setTimeout(() => { location.reload(); }, 3000);
    }
};

loadAvailableCards();

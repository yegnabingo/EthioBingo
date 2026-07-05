// ==========================================
// 📡 የቴሌግራም እና የሰርቨር ግንኙነት ቅንብር
// ==========================================
const tg = window.Telegram ? window.Telegram.WebApp : null;
let telegramId = "123456789"; // ፎልባክ ዲሞ አይዲ
let username = "Guest Player";

if (tg) {
    tg.ready();
    tg.expand();
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        telegramId = tg.initDataUnsafe.user.id.toString();
        username = tg.initDataUnsafe.user.username || tg.initDataUnsafe.user.first_name || "Player";
    }
}

// ኤለመንቶችን ከ HTML መያዝ
const pickScreen = document.getElementById("pickScreen");
const drawScreen = document.getElementById("drawScreen");
const cardGrid = document.getElementById("cardGrid");
const timerText = document.getElementById("timerText");
const confirmBtn = document.getElementById("confirmBtn");
const playerBingoCardContainer = document.getElementById("playerBingoCard");
const usernameEl = document.getElementById("username");

if (usernameEl) usernameEl.innerText = username;

let selectedCard = null;
let myPickedCards = []; // ተጫዋቹ የገዛቸው የካርድ ቁጥሮች (እስከ 5)
let activeGameLoop = null;

// ==========================================
// 1️⃣ PICK PHASE: የ1-200 ካርዶች አስተዳደር
// ==========================================
async function loadAvailableCards() {
    if (!cardGrid) return;
    cardGrid.innerHTML = "";

    try {
        // የትኞቹ ካርዶች እንደተያዙ ከሰርቨር መጠየቅ
        const response = await fetch("/api/cards/status");
        const takenCards = await response.json(); // [3, 14, 25...] የመሰለ ሊስት ይጠብቃል

        for (let i = 1; i <= 200; i++) {
            const card = document.createElement("div");
            card.className = "card-box";
            card.innerText = i;
            card.dataset.number = i;

            if (takenCards.includes(i)) {
                card.classList.add("taken"); // ቀድሞ የተያዘ (Locked)
            } else {
                card.onclick = () => {
                    if (card.classList.contains("taken")) return;
                    
                    document.querySelectorAll(".card-box.selected")
                        .forEach(c => c.classList.remove("selected"));

                    selectedCard = i;
                    card.classList.add("selected");
                };
            }
            cardGrid.appendChild(card);
        }
    } catch (err) {
        console.error("ካርዶችን መጫን አልተቻለም:", err);
    }
}

// CONFIRM PICKS አዝራር
if (confirmBtn) {
    confirmBtn.onclick = async () => {
        if (!selectedCard) { alert("እባክዎ መጀመሪያ ካርድ ይምረጡ!"); return; }
        if (myPickedCards.length >= 5) { alert("ከ 5 ካርድ በላይ መምረጥ አይቻልም!"); return; }

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
                if (el) {
                    el.classList.remove("selected");
                    el.classList.add("taken"); // ወዲያውኑ Lock ሆነ!
                }
                alert(`ካርድ ቁጥር ${selectedCard} በተሳካ ሁኔታ ተቆልፏል!`);
                selectedCard = null;
            } else {
                alert(result.message);
            }
        } catch (err) {
            console.error(err);
        }
    };
}

// ==========================================
// ⏱ የ30 ሰከንድ COUNTDOWN አስተዳደር (ከነጠላ ምንጭ)
// ==========================================
// ማሳሰቢያ፡ ሰዓቱ በሰርቨር ቢመራ ይመረጣል፣ ነገር ግን ለጊዜው በፊቱ ገጽ ላይ እንዲቆጥር ይኸው፡
let seconds = 30;
const startTimer = setInterval(() => {
    seconds--;
    if (timerText) timerText.innerText = seconds;

    if (seconds <= 0) {
        clearInterval(startTimer);
        switchToDrawScreen();
    }
}, 1000);

// ==========================================
// 2️⃣ DRAW PHASE: ወደ ቢንጎ እጣ ገጽ መሸጋገር
// ==========================================
async function switchToDrawScreen() {
    if (pickScreen) pickScreen.style.display = "none";
    if (drawScreen) drawScreen.style.display = "block";

    generateBingoBoard75();
    
    // 📂 ዲሞ ካርዱን አጥፍቶ የተጫዋቹን እውነተኛ ካርዶች ከዳታቤዝ ማምጣት
    if (myPickedCards.length > 0) {
        await fetchAndRenderPlayerCards();
    } else {
        playerBingoCardContainer.innerHTML = "<p style='color:grey; padding:20px;'>የመረጡት ካርድ የለም። እጣውን በመመልከት ላይ ነዎት...</p>";
    }
}

// የ1-75 ሰሌዳ መፍጠሪያ
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

// እውነተኛ የተጫዋች ካርዶችን (5x5) ከዳታቤዝ አምጥቶ መሳል
async function fetchAndRenderPlayerCards() {
    if (!playerBingoCardContainer) return;
    playerBingoCardContainer.innerHTML = "";

    try {
        // የመጀመሪያውን የመረጠውን ካርድ ዳታ ማምጣት (ብዙ ከመረጠ በሊስት ማምጣት ይቻላል)
        const response = await fetch(`/api/cards/get_matrix?card_number=${myPickedCards[0]}`);
        const cardData = await response.json(); // { matrix: [[...], [...]] }

        if (cardData && cardData.matrix) {
            renderBingoMatrix(cardData.matrix);
        }
    } catch (err) {
        console.error("የቢንጎ ካርድ ማምጣት አልተቻለም:", err);
    }
}

function renderBingoMatrix(matrix) {
    // የላዕላይ ፊደላት B I N G O
    const letters = ["B", "I", "N", "G", "O"];
    letters.forEach(l => {
        const cell = document.createElement("div");
        cell.className = "bingo-cell letter-cell";
        cell.innerText = l;
        playerBingoCardContainer.appendChild(cell);
    });

    // 5x5 ቁጥሮች
    matrix.forEach((row, rowIndex) => {
        row.forEach((val, colIndex) => {
            const cell = document.createElement("div");
            cell.className = "bingo-cell";
            cell.dataset.value = val; // ለቁጥር ማርኪንግ እንዲያመች

            if (val === "FREE") {
                cell.classList.add("free-cell");
                cell.innerText = "★";
                cell.classList.add("marked"); // ኮከብ ሁልጊዜ ማርክድ ነው
            } else {
                cell.innerText = val;
            }
            playerBingoCardContainer.appendChild(cell);
        });
    });
}

// ==========================================
// 📡 3️⃣ WEB ARRAY & WEBSOCKET: የቀጥታ እጣ እና Auto-Marking
// ==========================================
const protocol = location.protocol === "https:" ? "wss" : "ws";
const socket = new WebSocket(protocol + "://" + location.host + "/ws");

socket.onmessage = function (event) {
    try {
        const data = JSON.parse(event.data);

        // ሀ. አዲስ ኳስ ሲጣል (በየ2 ሰከንዱ ከሰርቨር የሚመጣ)
        if (data.type === "ball") {
            const ballNumber = data.number;

            // 1. የ1-75 ሰሌዳ ላይ ማብራት
            const ballEl = document.getElementById("ball-" + ballNumber);
            if (ballEl) ballEl.classList.add("called");

            // 2. 🟢 AUTO-MARKING LOGIC: ካርዳችን ላይ ካለ በራሱ ማርክ ያደርጋል!
            const matchingCells = document.querySelectorAll(`.bingo-cell[data-value="${ballNumber}"]`);
            matchingCells.forEach(cell => {
                cell.classList.add("marked"); // CSS ላይ .marked { background: #3b82f6; } ጨምር
            });

            // 3. የቅርብ ጊዜ ኳሶች ማሳያ ላይ ማዘመን (ከተፈለገ)
            updateRecentBallsDisplay(ballNumber);
        }

        // ለ. ጨዋታው ሲያልቅ (Winner ከተገኘ)
        if (data.type === "game_over") {
            alert(` ጨዋታው ተጠናቋል!\nአሸናፊ፡ ${data.winner_name}\nሽልማት፡ ${data.prize} ETB`);
            // ገጹን ከጥቂት ሰከንዶች በኋላ ለቀጣዩ ዙር ማዘጋጀት
            setTimeout(() => {
                location.reload();
            }, 5000);
        }

    } catch (e) {
        console.error("የዌብሶኬት መረጃ ስህተት:", e);
    }
};

// የቅርብ ኳሶችን በስክሪኑ ላይ ማስተላለፊያ
function updateRecentBallsDisplay(newBall) {
    const recentContainers = document.querySelectorAll(".recent-ball");
    if(recentContainers.length === 0) return;
    
    // የቆዩትን ወደ ኋላ ማስተላለፍ
    for (let i = recentContainers.length - 1; i > 0; i--) {
        recentContainers[i].innerText = recentContainers[i-1].innerText;
    }
    recentContainers[0].innerText = newBall;
}

// ገጹ መጀመሪያ ሲከፈት 1-200 ካርዶችን መጫን
loadAvailableCards();


// ==========================================
// 📡 1. የቴሌግራም መረጃን ማውጣት
// ==========================================
const tg = window.Telegram ? window.Telegram.WebApp : null;
let telegramId = "123456789"; // ፎልባክ አይዲ (በብሮውዘር ለመሞከር)

if (tg) {
    tg.ready();
    tg.expand();
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        telegramId = tg.initDataUnsafe.user.id.toString();
    }
}

const pickScreen = document.getElementById("pickScreen") || document.body; 
const drawScreen = document.getElementById("drawScreen");
const cardGrid = document.getElementById("cardGrid");
const timerText = document.getElementById("timerText");
const confirmBtn = document.getElementById("confirmBtn");
const playerBingoCardContainer = document.getElementById("playerBingoCard");

let selectedCard = null;
let myPickedCards = []; // ተጫዋቹ የገዛቸውን ካርዶች በሊስት ይይዛል
let socket;

// ==========================================
// 🟢 2. የ 1-200 ካርዶችን ሰሌዳ መሳል
// ==========================================
async function loadAvailableCards() {
    if (!cardGrid) return;
    cardGrid.innerHTML = "";
    
    let takenCards = [];
    try {
        const response = await fetch("/api/cards/status");
        if (response.ok) {
            takenCards = await response.json();
        }
    } catch (err) {
        console.log("የተያዙ ካርዶችን ማምጣት አልተቻለም፡", err);
    }

    if (!Array.isArray(takenCards)) takenCards = [];

    for (let i = 1; i <= 200; i++) {
        const card = document.createElement("div");
        card.className = "card-box";
        card.innerText = i;
        card.dataset.number = i;

        if (takenCards.includes(i)) {
            card.classList.add("taken");
        } else {
            card.onclick = () => {
                if (card.classList.contains("taken")) return;
                document.querySelectorAll(".card-box.selected").forEach(c => c.classList.remove("selected"));
                selectedCard = i;
                card.classList.add("selected");
            };
        }
        cardGrid.appendChild(card);
    }
}

// ==========================================
// 🎯 3. ካርድ መግዣ ቁልፍ (Confirm Picks)
// ==========================================
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
                myPickedCards.push(selectedCard); // የተገዛውን ካርድ ቁጥር መመዝገብ
                alert(`ቁጥር ${selectedCard} ካርድ በትክክል ተገዝቷል! ዕጣ ሲጀምር ማትሪክሱ ከዳታቤዝ ይመጣል`);
                loadAvailableCards(); // ሰሌዳውን በድጋሚ ማደስ (taken እንዲሆን)
            } else {
                alert("ስህተት: " + result.message);
            }
        } catch (err) {
            console.error("Pick Error:", err);
        }
    };
}

// ==========================================
// 🔄 4. ወደ DRAW SCREEN መቀየር እና እውነተኛ ካርድ ማሳየት
// ==========================================
async function switchToDrawScreen() {
    // ገጾቹን መለዋወጥ
    const mainPickView = document.querySelector(".container") || pickScreen;
    if (mainPickView) mainPickView.style.display = "none";
    if (drawScreen) {
        drawScreen.style.display = "block";
        drawScreen.style.visibility = "visible";
    }
    
    // የ 1-75 ዕጣ ሰሌዳ ማዘጋጀት
    generateBingoBoard75();
    
    // 💡 [ዋናው ማስተካከያ] ተጫዋቹ የገዛው ካርድ ካለ እውነተኛውን ማትሪክስ ከዳታቤዝ ማምጣት
    if (myPickedCards.length > 0) {
        const lastPickedCard = myPickedCards[myPickedCards.length - 1]; // የመጨረሻውን የገዛውን ካርድ መውሰድ
        await fetchAndRenderDatabaseMatrix(lastPickedCard);
    } else {
        // ካርድ ካልገዛ ባዶ ማትሪክስ ማሳየት (ወይም መልዕክት)
        if (playerBingoCardContainer) {
            playerBingoCardContainer.innerHTML = "<div style='color:white; text-align:center; grid-column: span 5;'>በዚህ ዙር ካርድ አልገዙም!</div>";
        }
    }
}

// 📦 እውነተኛውን ማትሪክስ ከዳታቤዝ አምጥቶ የሚስለው ተግባር
async function fetchAndRenderDatabaseMatrix(cardNumber) {
    if (!playerBingoCardContainer) return;
    playerBingoCardContainer.innerHTML = "";
    
    try {
        // ባክኤንድ ላይ ወደ ፈጠርነው የ get_matrix መንገድ መጥራት
        const response = await fetch(`/api/cards/get_matrix?card_number=${cardNumber}`);
        if (!response.ok) throw new Error("Matrix fetch failed");
        
        const data = await response.json();
        const matrix = data.matrix; // ይህ ከባክኤንድ የመጣው የ 5x5 አሬይ ነው

        // ማትሪክሱን በስክሪኑ ላይ መሳል
        matrix.forEach(row => {
            row.forEach(val => {
                const cell = document.createElement("div");
                cell.className = "bingo-cell";
                cell.dataset.value = val; // ለኳስ መምቻ እንዲያገለግል ቁጥሩን መያዝ

                if (val === "FREE" || val === "★") {
                    cell.classList.add("marked");
                    cell.innerText = "★";
                } else {
                    cell.innerText = val;
                }
                playerBingoCardContainer.appendChild(cell);
            });
        });
        console.log(`✅ የካርድ ቁጥር ${cardNumber} እውነተኛ ማትሪክስ ከዳታቤዝ ተስሏል።`);
    } catch (err) {
        console.error("ዳታቤዝ ማትሪክስ ስህተት:", err);
    }
}

// 1-75 የኳስ መውረጃ ሰሌዳ መፍጠሪያ
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

// ==========================================
// 📡 5. የዌብሶኬት ግንኙነት እና የሰዓት መቆጣጠሪያ
// ==========================================
function connectWebSocket() {
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    socket = new WebSocket(protocol + "://" + location.host + "/ws");

    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        
        // ሀ. የሰዓት መቁጠሪያ መልዕክት
        if (data.type === "time_update") {
            if (timerText) timerText.innerText = data.time + "s";
            
            // የ 30 ሰከንድ መከላከያ፡ 0 ሲደርስ ራሱ እንዲቀይር
            if (data.time === 0) {
                switchToDrawScreen();
            }
        }
        
        // ለ. የPhase መቀየሪያ መልዕክት
        if (data.type === "phase_change" && data.phase === "DRAW") {
            switchToDrawScreen();
        }
        
        // ሐ. አውቶማቲክ የሚወርዱ ኳሶች (1-75)
        if (data.type === "ball") {
            // 1. በ 1-75 ሰሌዳ ላይ ኳሱን ማብራት
            const ballEl = document.getElementById("ball-" + data.number);
            if (ballEl) ballEl.classList.add("called");

            // 2. በተጫዋቹ 5x5 ካርድ ላይ ቁጥሩ ካለ በራስ-ሰር መምታት (Mark ማድረግ)
            document.querySelectorAll(".bingo-cell").forEach(cell => {
                if (cell.dataset.value == data.number) {
                    cell.classList.add("marked");
                }
            });
        }
    };

    socket.onclose = function() {
        console.log("ዌብሶኬት ተቋርጧል፣ በ3 ሰከንድ ውስጥ መልሶ ይገናኛል...");
        setTimeout(connectWebSocket, 3000);
    };
}

// ጨዋታውን ማስጀመር
loadAvailableCards();
connectWebSocket();

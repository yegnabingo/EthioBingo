// 📡 የዌብሶኬት እና የጨዋታው ግሎባል ተለዋዋጮች
let ws;
let selectedCards = []; // በአሁኑ ዙር ተጫዋቹ የገዛቸው የካርድ ቁጥሮች (Max 5)
let currentBetAmount = 10; // ነባሪ ውርርድ መጠን
let myTelegramId = "TG-" + Math.floor(10000 + Math.random() * 90000); // ለሙከራ የሚሆን ራንደም ID (በቴሌግራም ቦት ሲሆን በራስ-ሰር ይተካል)

// 🔊 የድምፅ ሲስተም ፈንክሽን
function playBallSound(ballLabel) {
    try {
        // የድምፅ ፋይሎቹ static/sounds/ ማውጫ ውስጥ መኖር አለባቸው (ለምሳሌ፡ B12.mp3)
        const audio = new Audio(`/static/sounds/${ballLabel}.mp3`);
        audio.play();
    } catch (e) {
        console.log("የድምፅ ፋይል ማጫወት አልተቻለም፦", e);
    }
}

// 🔌 የዌብሶኬት ግንኙነት መክፈቻ
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(protocol + window.location.host + "/ws");

    ws.onopen = () => console.log("✅ ከዌብሶኬት ጋር ተገናኝተናል!");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // 1️⃣ የሰዓት መቁጠሪያ ምዕራፍ (PICK PHASE)
        if (data.type === "time_update" && data.phase === "PICK") {
            document.getElementById("phase-title").innerText = "ካርድ ይምረጡ (PICK PHASE)";
            document.getElementById("countdown").innerText = data.time + "s";
            document.getElementById("game-number").innerText = "የጨዋታ ቁጥር፦ #" + data.game_no;
            
            // 1-200 ገጽ መታየቱን ማረጋገጥ፡ 1-75 መደበቅ
            document.getElementById("pick-section").style.display = "block";
            document.getElementById("draw-section").style.display = "none";
            document.getElementById("winner-popup").style.display = "none";
        }

        // 2️⃣ የዕጣ መጀመሪያ ምዕራፍ (DRAW PHASE)
        if (data.type === "phase_change" && data.phase === "DRAW") {
            document.getElementById("phase-title").innerText = "ዕጣ እየወጣ ነው (DRAW PHASE)";
            document.getElementById("pick-section").style.display = "none";
            document.getElementById("draw-section").style.display = "block";

            // ተጫዋቹ የገዛቸው ካርዶች ካሉ 5x5 ማትሪክሳቸውን ከባክኤንድ ማምጣት
            renderMyBoughtCards();
        }

        // 3️⃣ የኳሶች መውረድ ምዕራፍ (BALL CALLING)
        if (data.type === "ball") {
            // ሀ. የወረደውን ኳስ በቦርዱ ላይ ማሳየት
            document.getElementById("current-ball").innerText = data.label; // ለምሳሌ፡ B12
            
            // ለ. የ 1-75 ሰሌዳ ላይ ቁጥሩን ማብራት
            const boardCell = document.getElementById(`board-ball-${data.number}`);
            if (boardCell) boardCell.classList.add("drawn");

            // ሐ. ድምፅ ማጫወት (B12, G58 እያለ ይጮሃል)
            playBallSound(data.label);

            // መ. AUTO MARKING: በተጫዋቹ 5x5 ካርዶች ላይ ቁጥሩ ካለ በራስ-ሰር ማብራት
            const matchingCells = document.querySelectorAll(`.card-cell-num-${data.number}`);
            matchingCells.forEach(cell => cell.classList.add("marked-auto"));
        }

        // 4️⃣ የጨዋታው ማክተም እና የአሸናፊ ማሳያ (GAME OVER)
        if (data.type === "game_over") {
            if (data.result === "BINGO") {
                showWinnerPopup(data.winner_name, data.winning_card, data.prize, data.message);
            } else {
                showWinnerPopup("ማንም የለም", "-", "0", data.message);
            }
            // ጨዋታው ሲያልቅ በሚቀጥለው ዙር አዲስ ካርድ ለመግዛት የድሮውን ዝርዝር ማጽዳት
            selectedCards = [];
            resetMainBoard();
        }
    };

    ws.onclose = () => setTimeout(connectWebSocket, 2000); // ቢቋረጥ መልሶ ያገናኛል
}

// 💰 ካርድ ለመግዛት 'Confirm Pick' ሲነካ የሚሰራ
async function confirmPickCard(cardNumber) {
    // በአንድ ጨዋታ ከ 5 ካርድ በላይ መግዛት አይችልም
    if (selectedCards.length >= 5) {
        alert("በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርድ መጠን 5 ብቻ ነው!");
        return;
    }

    try {
        const response = await fetch("/api/cards/pick", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                telegram_id: myTelegramId,
                card_number: cardNumber,
                bet_amount: parseFloat(currentBetAmount)
            })
        });

        const result = await response.json();

        if (result.success) {
            selectedCards.push(cardNumber); // የገዛነውን ቁጥር መመዝገብ
            document.getElementById(`pick-card-${cardNumber}`).classList.add("bought");
            document.getElementById("user-balance").innerText = result.current_balance + " ETB";
            alert(result.message);
        } else {
            alert(result.message); // "በቂ ባላንስ የሎትም!" ወይም "ካርዱ ተይዟል!" የሚለውን ያሳያል
        }
    } catch (e) {
        alert("የግንኙነት ስህተት አጋጥሟል!");
    }
}

// 🎴 የተገዙትን ካርዶች (1-5 ሊሆኑ ይችላሉ) 5x5 ማትሪክስ አውጥቶ በ 1-75 ስር መደርደር
async function renderMyBoughtCards() {
    const container = document.getElementById("my-cards-container");
    container.innerHTML = ""; // ማጽዳት

    if (selectedCards.length === 0) {
        container.innerHTML = "<p class='no-card'>በዚህ ዙር ምንም ካርድ አልገዙም!</p>";
        return;
    }

    // ለእያንዳንዱ የገዛነው ካርድ የ 5x5 ማትሪክስ ጥሪ ማድረግ
    for (let cardNum of selectedCards) {
        try {
            const res = await fetch(`/api/cards/get_matrix?card_number=${cardNum}`);
            const data = await res.json();
            const matrix = data.matrix;

            // የካርዱን HTML መዋቅር መገንባት
            const cardGrid = document.createElement("div");
            cardGrid.className = "bingo-card-box";
            
            let html = `
                <div class="card-header-title">ካርድ #${cardNum}</div>
                <div class="bingo-headers"><span>B</span><span>I</span><span>N</span><span>G</span><span>O</span></div>
                <div class="bingo-grid-5x5">
            `;

            // 5x5 ማትሪክሱን በሉፕ መሳል
            matrix.forEach((row, rowIndex) => {
                row.forEach((cell, colIndex) => {
                    if (cell === "FREE") {
                        html += `<div class="bingo-cell free-space">★ FREE</div>`;
                    } else {
                        // MANUAL MARKING እንዲሰራ click ስናደርግ 'marked-manual' ክላስ እንጨምራለን
                        html += `
                            <div class="bingo-cell card-cell-num-${cell}" onclick="this.classList.toggle('marked-manual')">
                                ${cell}
                            </div>`;
                    }
                });
            });

            html += `</div>`;
            cardGrid.innerHTML = html;
            container.appendChild(cardGrid);

        } catch (e) {
            console.log("ማትሪክስ መሳል አልተቻለም", e);
        }
    }
}

// 🏆 የአሸናፊዎችን ፖፕ-አፕ ማሳያ
function showWinnerPopup(name, card, prize, message) {
    const popup = document.getElementById("winner-popup");
    popup.innerHTML = `
        <div class="winner-modal-content">
            <h2>🎉 🚀 ቢንጎ ተበላ! 🚀 🎉</h2>
            <p class="winner-msg">${message}</p>
            <div class="winner-stats">
                <p><b>አሸናፊ፦</b> ${name}</p>
                <p><b>ካርድ ቁጥር፦</b> #${card}</p>
                <p><b>የሽልማት መጠን፦</b> <span class="prize-text">${prize} ETB</span></p>
            </div>
        </div>
    `;
    popup.style.display = "flex";
}

// 🔄 አዲስ ዙር ሲጀምር የድሮውን የ 1-75 ሰሌዳ ማጽጃ
function resetMainBoard() {
    for (let i = 1; i <= 75; i++) {
        const cell = document.getElementById(`board-ball-${i}`);
        if (cell) cell.classList.remove("drawn");
    }
    document.getElementById("current-ball").innerText = "-";
}

// 💵 የውርርድ መጠን መቀየሪያ (10, 20, 50 ብር ሲነካ)
function setBetAmount(amount) {
    currentBetAmount = amount;
    // ንቁ መሆኑን በ CSS ለማሳየት
    document.querySelectorAll(".bet-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`bet-btn-${amount}`).classList.add("active");
}

// 🚀 ገጹ ሲከፈት መጀመሪያ ስራ ማስጀመር
window.onload = () => {
    connectWebSocket();
    
    // የውርርድ በተኖችን ማዘጋጀት
    document.getElementById("bet-btn-10").onclick = () => setBetAmount(10);
    document.getElementById("bet-btn-20").onclick = () => setBetAmount(20);
    document.getElementById("bet-btn-50").onclick = () => setBetAmount(50);
};

// 📡 የዌብሶኬት እና የጨዋታው ግሎባል ተለዋዋጮች
let ws;
let temporarilySelectedCards = []; // 💡 ለጊዜው የተመረጡ (ገና ያልተገዙ) ካርዶች
let selectedCards = []; // 💰 በባክኤንድ የተረጋገጡ እና የተገዙ የካርድ ቁጥሮች (Max 5)
let currentBetAmount = 10; // ነባሪ ውርርድ መጠን
let myTelegramId = "TG-GUEST"; 
let myTelegramName = "ተጫዋች";

// 🌐 የቴሌግራም ሚኒ አፕ መረጃን ማንበብ
if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        myTelegramId = String(tg.initDataUnsafe.user.id);
        myTelegramName = tg.initDataUnsafe.user.first_name || "ተጫዋች";
    }
}

// 🔊 የድምፅ ሲስተም
function playBallSound(ballLabel) {
    try {
        const audio = new Audio(`/static/sounds/${ballLabel}.mp3`);
        audio.play();
    } catch (e) {
        console.log("የድምፅ ፋይል ማጫወት አልተቻለም፦", e);
    }
}

// 🔌 የዌብሶኬት ማገናኛ
function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(protocol + window.location.host + "/ws");

    ws.onopen = () => {
        console.log("✅ ከቢንጎ ሞተር ጋር ተገናኘን!");
        generate200Cards(); 
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // 1️⃣ PICK PHASE (ካርድ መምረጫ ሰዓት በየሰከንዱ ሲመጣ)
        if (data.type === "time_update") {
            if (data.phase === "PICK") {
                document.getElementById("pickScreen").style.display = "block";
                document.getElementById("drawScreen").style.display = "none";
                document.getElementById("timerText").innerText = data.time;
            }
            
            const statsBoxes = document.querySelectorAll(".stats-grid .stat-box strong");
            if (statsBoxes.length >= 3) {
                statsBoxes[0].innerText = data.game_no || "604606";
                statsBoxes[2].innerText = data.total_players || "84";
            }
            
            const oldPopup = document.getElementById("winner-popup");
            if (oldPopup) oldPopup.remove();
        }

        // 2️⃣ PHASE CHANGE ➔ ወደ DRAW PHASE መሸጋገሪያ
        if (data.type === "phase_change" && data.phase === "DRAW") {
            document.getElementById("pickScreen").style.display = "none";
            document.getElementById("drawScreen").style.display = "block";
            
            clear75Board();
            renderMyBoughtCards();
        }

        // 3️⃣ BALL PHASE (ኳስ ሲወድቅ)
        if (data.type === "ball") {
            document.getElementById("pickScreen").style.display = "none";
            document.getElementById("drawScreen").style.display = "block";

            const liveBall = document.querySelector(".recent-ball.live");
            if (liveBall) liveBall.innerText = data.label;

            const ballElement = document.getElementById(`ball-${data.number}`);
            if (ballElement) ballElement.classList.add("drawn");

            playBallSound(data.label);

            const matchingCells = document.querySelectorAll(`.cell-${data.number}`);
            matchingCells.forEach(cell => {
                cell.classList.add("marked-auto");
                cell.style.background = "#ff4757";
            });
            
            const callCountEl = document.getElementById("callCount");
            if (callCountEl) callCountEl.innerText = data.call_count;
        }

        // 4️⃣ GAME OVER (ጨዋታ ሲያልቅ)
        if (data.type === "game_over") {
            showWinnerPopup(data.message || "ዙሩ ተጠናቋል።");
            selectedCards = []; 
            temporarilySelectedCards = []; // ጊዜያዊውንም ማጽዳት
            
            document.querySelectorAll(".card-btn").forEach(btn => {
                btn.classList.remove("bought");
                btn.classList.remove("selected-temp");
            });
        }
    };

    ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

// 🎴 1-200 የካርድ መምረጫ አዝራሮችን HTML ላይ መፍጠር
function generate200Cards() {
    const grid = document.getElementById("cardGrid");
    if (!grid) return;
    grid.innerHTML = "";
    
    for (let i = 1; i <= 200; i++) {
        const btn = document.createElement("button");
        btn.className = "card-btn";
        btn.id = `pick-card-${i}`;
        btn.innerText = i;
        btn.onclick = () => selectCardTemporarily(i); // 💡 መጀመሪያ ለጊዜው ብቻ ይመርጣል
        grid.appendChild(btn);
    }
}

// 💡 1. ቁጥር ሲነካ ለጊዜው መምረጫ ወይም መሰረዣ ሎጂክ
function selectCardTemporarily(cardNumber) {
    const btn = document.getElementById(`pick-card-${cardNumber}`);
    
    // ካርዱ ቀድሞ ከተገዛ ምንም አያድርግ
    if (selectedCards.includes(cardNumber)) return;

    // ቀድሞ ለጊዜው ተመርጦ ከሆነ መልሶ መሰረዝ (Deselect)
    if (temporarilySelectedCards.includes(cardNumber)) {
        temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
        if (btn) btn.classList.remove("selected-temp"); // የCSS ምርጫ ማጥፊያ
        return;
    }

    // በአንድ ጨዋታ ከ 5 ካርድ በላይ መምረጥ አይቻልም
    if (temporarilySelectedCards.length + selectedCards.length >= 5) {
        alert("በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርድ መጠን 5 ብቻ ነው!");
        return;
    }

    // ለጊዜው መመዝገብ
    temporarilySelectedCards.push(cardNumber);
    if (btn) btn.classList.add("selected-temp"); // ስክሪን ላይ ተመርጦ እንዲታይ ማድረግ
}

// 💰 2. CONFIRM PICKS አዝራር ሲነካ ብቻ በአንድነት ወደ ዳታቤዝ የሚልክ ሎጂክ
async function confirmAllSelectedPicks() {
    if (temporarilySelectedCards.length === 0) {
        alert("እባክህ መጀመሪያ የሚገዙትን የካርድ ቁጥሮች ካረንጓዴው ሰሌዳ ላይ ይምረጡ!");
        return;
    }

    console.log("ያለፉት ካርዶች አንድ በአንድ እየተላኩ ነው...", temporarilySelectedCards);
    
    // የገዛናቸውን አንድ በአንድ ወደ ባክኤንድ መላክ (One-by-One ህግ መሰረት)
    for (let cardNumber of [...temporarilySelectedCards]) {
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
                selectedCards.push(cardNumber);
                // ጊዜያዊውን ዝርዝር ማጽዳት
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected-temp");
                    btn.classList.add("bought"); // የተገዛ መሆኑን ማሳያ
                }

                // የWallet ባላንስ ማደሻ
                const statsBoxes = document.querySelectorAll(".stats-grid .stat-box strong");
                if (statsBoxes.length >= 4) {
                    statsBoxes[3].innerText = result.current_balance + " ETB";
                }
            } else {
                alert(`ካርድ ቁጥር #${cardNumber} መግዛት አልተቻለም፦ ${result.message}`);
            }
        } catch (e) {
            alert("የመግዛት ስህተት አጋጥሟል!");
        }
    }
    
    alert("የመረጧቸው ካርዶች በተሳካ ሁኔታ ተረጋግጠው ተገዝተዋል!");
}

// 🎴 የ 1-75 ቦርድ መፍጠሪያ
function clear75Board() {
    const containers = {
        "b": document.getElementById("b-container"),
        "i": document.getElementById("i-container"),
        "n": document.getElementById("n-container"),
        "g": document.getElementById("g-container"),
        "o": document.getElementById("o-container")
    };

    Object.values(containers).forEach(c => { if(c) c.innerHTML = ""; });

    for (let num = 1; num <= 75; num++) {
        const numDiv = document.createElement("div");
        numDiv.className = "board-num";
        numDiv.id = `ball-${num}`;
        numDiv.innerText = num;

        if (num <= 15) containers["b"].appendChild(numDiv);
        else if (num <= 30) containers["i"].appendChild(numDiv);
        else if (num <= 45) containers["n"].appendChild(numDiv);
        else if (num <= 60) containers["g"].appendChild(numDiv);
        else containers["o"].appendChild(numDiv);
    }
}

// 🎴 የገዛናቸውን የካርዶች 5x5 ማትሪክስ መሳያ
async function renderMyBoughtCards() {
    const container = document.getElementById("playerBingoCard");
    if (!container) return;
    container.innerHTML = "";

    if (selectedCards.length === 0) {
        container.innerHTML = "<div style='color:white; text-align:center; padding:20px;'>በዚህ ዙር ምንም ካርድ አልገዙም!</div>";
        return;
    }

    for (let cardNum of selectedCards) {
        try {
            const res = await fetch(`/api/cards/get_matrix?card_number=${cardNum}`);
            const data = await res.json();
            const matrix = data.matrix;

            const cardWrapper = document.createElement("div");
            cardWrapper.className = "single-card-view";
            cardWrapper.style.marginBottom = "20px";

            let html = `
                <div style="color:#ffd700; font-weight:bold; text-align:center; margin-bottom:5px;">ካርድ #${cardNum}</div>
                <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px;">
            `;

            matrix.forEach(row => {
                row.forEach(cell => {
                    if (cell === "FREE") {
                        html += `<div class="bingo-cell free" style="background:#ff4757; color:white; text-align:center; font-weight:bold; padding:8px 0; border-radius:4px;">★</div>`;
                    } else {
                        html += `
                            <div class="bingo-cell cell-${cell}" onclick="this.classList.toggle('marked-manual')" style="background:#2f3542; color:white; text-align:center; padding:8px 0; border-radius:4px; font-weight:bold; cursor:pointer;">
                                ${cell}
                            </div>`;
                    }
                });
            });

            html += `</div>`;
            cardWrapper.innerHTML = html;
            container.appendChild(cardWrapper);

        } catch (e) {
            console.log("ማትሪክስ መሳል አልተቻለም", e);
        }
    }
}

// 🏆 የቪአይፒ አሸናፊዎች ፖፕ-አፕ
function showWinnerPopup(message) {
    const popup = document.createElement("div");
    popup.id = "winner-popup";
    popup.style = "position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); display:flex; justify-content:center; align-items:center; z-index:9999; color:white; font-family:sans-serif;";
    
    popup.innerHTML = `
        <div style="background:#2f3542; border:2px solid #ffd700; border-radius:12px; padding:30px; text-align:center; max-width:85%; box-shadow:0 0 20px #ffd700;">
            <h1 style="color:#ffd700; margin-top:0; font-size:28px;">🎉 ቢንጎ ተጠናቀቀ! 🎉</h1>
            <p style="font-size:18px; line-height:1.6; margin:20px 0;">${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" style="background:#ffd700; color:black; border:none; padding:10px 25px; font-size:16px; font-weight:bold; border-radius:6px; cursor:pointer;">እሺ</button>
        </div>
    `;
    document.body.appendChild(popup);
}

// ገጹ ሲከፈት ስራ ማስጀመር
window.onload = () => {
    connectWebSocket();
    
    // 💡 [ዋና ማሻሻያ] HTML ላይ ያለው CONFIRM PICKS አዝራር ሲነካ የጋራ መግዣ ፈንክሽኑን እንዲጠራ ማድረግ
    const confirmBtn = document.getElementById("confirmBtn");
    if (confirmBtn) {
        confirmBtn.onclick = () => confirmAllSelectedPicks();
    }
};

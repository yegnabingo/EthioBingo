// 📡 የዌብሶኬት እና የጨዋታው ግሎባል ተለዋዋጮች
let ws;
let temporarilySelectedCards = []; 
let selectedCards = []; 
let currentBetAmount = 10; 
let myTelegramId = "TG-GUEST"; 
let myTelegramName = "ተጫዋች";

let currentCardIndex = 0; 
let recentBallsList = []; // የቅርብ 10 ኳሶች
let soundEnabled = true;

// 🌐 የቴሌግราม ሚኒ አፕ መረጃ
if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        myTelegramId = String(tg.initDataUnsafe.user.id);
        myTelegramName = tg.initDataUnsafe.user.first_name || "ተጫዋች";
    }
}

// 🎨 የቢንጎ ፊደላት ቀለማትን በቋሚነት መለኪያ ፈንክሽን
function getBingoColor(letter) {
    switch(letter) {
        case 'B': return '#2ed573'; // አረንጓዴ
        case 'I': return '#ff4757'; // ቀይ
        case 'N': return '#ffa500'; // ወርቃማ / ብርቱካንማ
        case 'G': return '#1e90ff'; // ሰማያዊ
        case 'O': return '#9b59b6'; // ሀምራዊ
        default: return '#2f3542';
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    ws = new WebSocket(protocol + window.location.host + "/ws");

    ws.onopen = () => {
        console.log("✅ ከቢንጎ ሞተር ጋር ተገናኘን!");
        generate200Cards(); 
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // 🆕 [አዲሱ ሎጂክ] ማንኛውም ሰው ካርድ ሲገዛ ሰርቨሩ የሁሉንም ዝርዝር ሲልክ ቀለማቸውን መቀየር
        if (data.type === "taken_cards_update") {
            update200CardsColors(data.taken_cards);
        }

        // 1️⃣ PICK PHASE
        if (data.type === "time_update" && data.phase === "PICK") {
            document.getElementById("pickScreen").style.display = "block";
            document.getElementById("drawScreen").style.display = "none";
            document.getElementById("timerText").innerText = data.time;
            
            const statsBoxes = document.querySelectorAll(".stats-grid .stat-box strong");
            if (statsBoxes.length >= 3) {
                statsBoxes[0].innerText = data.game_no;
                statsBoxes[2].innerText = data.total_players || "1";
            }
            
            const oldPopup = document.getElementById("winner-popup");
            if (oldPopup) oldPopup.remove();
            
            recentBallsList = [];
        }

        // 2️⃣ PHASE CHANGE ➔ ወደ DRAW PHASE መሸጋገሪያ
        if (data.type === "phase_change" && data.phase === "DRAW") {
            document.getElementById("pickScreen").style.display = "none";
            document.getElementById("drawScreen").style.display = "block";
            
            const gameMetaSpan = document.querySelector(".game-meta span");
            if (gameMetaSpan) gameMetaSpan.innerText = "Game " + data.game_no;
            
            const totalPlayers = data.total_players || 1;
            if(document.getElementById("stakeAmt")) document.getElementById("stakeAmt").innerText = currentBetAmount;
            if(document.getElementById("derashAmt")) document.getElementById("derashAmt").innerText = (totalPlayers * currentBetAmount * 0.8).toFixed(0);
            if(document.getElementById("playerCount")) document.getElementById("playerCount").innerText = totalPlayers;

            clear75Board();
            currentCardIndex = 0; 
            renderMyBoughtCards();
            updateRecentBallsUI(); 
        }

        // 3️⃣ BALL PHASE (ኳስ ሲወድቅ)
        if (data.type === "ball") {
            document.getElementById("pickScreen").style.display = "none";
            document.getElementById("drawScreen").style.display = "block";

            const ballElement = document.getElementById(`ball-${data.number}`);
            const letter = data.label.charAt(0);
            const color = getBingoColor(letter);
            
            if (ballElement) {
                ballElement.classList.add("drawn");
                ballElement.style.background = color;
                ballElement.style.color = "#fff";
                ballElement.style.boxShadow = `0 0 10px ${color}`;
            }

            // 🔴 ኳሱን ወደ ዝርዝር መጨመር
            recentBallsList.unshift({ label: data.label, letter: letter, num: data.number });
            if (recentBallsList.length > 10) recentBallsList.pop();
            updateRecentBallsUI(); 

            // AUTO MARKING
            const matchingCells = document.querySelectorAll(`.cell-${data.number}`);
            matchingCells.forEach(cell => {
                cell.classList.add("marked-auto");
                cell.style.background = color;
                cell.style.color = "#fff";
                cell.style.boxShadow = `0 0 12px ${color}`;
            });
            
            if (document.getElementById("callCount")) {
                document.getElementById("callCount").innerText = data.call_count;
            }
        }

        // 4️⃣ GAME OVER
        if (data.type === "game_over") {
            showWinnerPopup(data.message || "ዙሩ ተጠናቋል።");
            selectedCards = []; 
            temporarilySelectedCards = [];
            
            // የካርድ ቁልፎችን ወደ መደበኛ ነጭ መመለስ (አዲስ ዙር ስለጀመረ)
            document.querySelectorAll(".card-btn").forEach(btn => {
                btn.style.backgroundColor = "#ffffff";
                btn.style.color = "#000000";
                btn.classList.remove("bought", "selected-temp");
            });
        }
    };

    ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

// 🎴 1-200 የካርድ መምረጫ አዝራሮች መፍጠሪያ (መነሻቸው ነጭ ነው)
function generate200Cards() {
    const grid = document.getElementById("cardGrid");
    if (!grid) return;
    grid.innerHTML = "";
    for (let i = 1; i <= 200; i++) {
        const btn = document.createElement("button");
        btn.className = "card-btn";
        btn.id = `pick-card-${i}`;
        btn.innerText = i;
        btn.style.backgroundColor = "#ffffff"; // መነሻ ቀለም፡ ነጭ 🤍
        btn.style.color = "#000000";
        btn.onclick = () => selectCardTemporarily(i);
        grid.appendChild(btn);
    }
}

// 🎨 [አዲሱ ፈንክሽን] የተያዙትን ቢጫ፣ ያልተያዙትን ነጭ ማድረጊያ
function update200CardsColors(takenCardsList) {
    for (let i = 1; i <= 200; i++) {
        const btn = document.getElementById(`pick-card-${i}`);
        if (!btn) continue;

        // እኔ ራሴ የመረጥኳቸው በጊዜያዊነት ሰማያዊ ሆነው ይቆዩ
        if (temporarilySelectedCards.includes(i)) {
            continue;
        }

        if (takenCardsList.includes(i)) {
            btn.style.backgroundColor = "#ffcc00"; // የተያዘ ቁጥር፡ ደማቅ ቢጫ 💛
            btn.style.color = "#000000";
            btn.classList.add("bought");
        } else {
            btn.style.backgroundColor = "#ffffff"; // ያልተያዘ ቁጥር፡ ነጭ 🤍
            btn.style.color = "#000000";
            btn.classList.remove("bought");
        }
    }
}

function selectCardTemporarily(cardNumber) {
    const btn = document.getElementById(`pick-card-${cardNumber}`);
    if (selectedCards.includes(cardNumber)) return;

    if (temporarilySelectedCards.includes(cardNumber)) {
        temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
        // ምርጫውን ሲያነሳው የተያዘ ከሆነ ወደ ቢጫ ካልሆነ ወደ ነጭ መመለስ
        if (btn) {
            btn.classList.remove("selected-temp");
            btn.style.backgroundColor = btn.classList.contains("bought") ? "#ffcc00" : "#ffffff";
        }
        return;
    }

    if (temporarilySelectedCards.length + selectedCards.length >= 5) {
        showToastMessage("⚠️ በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርድ መጠን 5 ብቻ ነው!", "error");
        return;
    }

    temporarilySelectedCards.push(cardNumber);
    if (btn) {
        btn.classList.add("selected-temp");
        btn.style.backgroundColor = "#1e90ff"; // በጊዜያዊነት የተመረጠው ሰማያዊ ይሆናል
        btn.style.color = "#fff";
    }
}

// 🎯 100% የተስተካከለ የ Confirm Picks ቁልፍ ሎጂክ
async function confirmAllSelectedPicks() {
    if (temporarilySelectedCards.length === 0) {
        showToastMessage("⚠️ እባክህ መጀመሪያ የሚገዙትን የካርድ ቁጥሮች ይምረጡ!", "error");
        return;
    }

    // በአንድ ጊዜ ሁሉንም ለመግዛት ሉፕ ውስጥ እናስገባዋለን
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

            // ❌ 1. ብር ከሌለው (Insufficient Balance)
            if (result.success === false) {
                showToastMessage("⚠️ " + result.message, "error");
                
                // የጊዜያዊ ምርጫ ቀለማቸውን መልሰን ነጭ ወይም ቢጫ እናደርጋቸዋለን
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected-temp");
                    btn.style.backgroundColor = btn.classList.contains("bought") ? "#ffcc00" : "#ffffff";
                    btn.style.color = "#000000";
                }
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                continue; // ወደ ቀጣዩ ካርድ ይሻገራል
            }

            // ✅ 2. ግዢው ከተሳካ (Success)
            if (result.success === true) {
                selectedCards.push(cardNumber);
                // ከጊዜያዊ ዝርዝር ውስጥ ማጽዳት
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected-temp");
                    btn.classList.add("bought");
                    btn.style.backgroundColor = "#ffcc00"; // አሁን የተገዛውን ወደ ቢጫ መቀየር 💛
                    btn.style.color = "#000000";
                }

                // በላይኛው ስክሪን ላይ ያለውን የተጫዋቹን ባላንስ በቅጽበት ማደስ
                const statsBoxes = document.querySelectorAll(".stats-grid .stat-box strong");
                if (statsBoxes.length >= 4) {
                    statsBoxes[3].innerText = result.current_balance + " ETB";
                }
                
                showToastMessage("🎉 ካርዱ በተሳካ ሁኔታ ተገዝቷል!", "success");
            }
        } catch (e) {
            console.log(e);
            showToastMessage("⚠️ የቴክኒክ ስህተት አጋጥሟል!", "error");
        }
    }
}

// ⏱️ የመልዕክት ሳጥኑ መጥሪያ እና ከ 2 ሰከንድ በኋላ በራሱ ማጥፊያ (Auto-dismiss Toast)
function showToastMessage(message, type) {
    const oldToast = document.getElementById("live-toast");
    if (oldToast) oldToast.remove(); // የቆየ ካለ ማጽዳት

    const toast = document.createElement("div");
    toast.id = "live-toast";
    
    // ውብ የአረንጓዴ እና ቀይ ቀለም ስታይል
    let bgColor = type === "success" ? "#2ecc71" : "#e74c3c";
    
    toast.style = `
        position: fixed; top: 20%; left: 50%; transform: translate(-50%, -50%);
        background: ${bgColor}; color: white; padding: 14px 24px; border-radius: 8px;
        font-size: 16px; font-weight: bold; z-index: 9999; text-align: center;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3); transition: opacity 0.3s ease;
    `;
    toast.innerText = message;
    document.body.appendChild(toast);

    // ⏳ ከ 2 ሰከንድ (2000ms) በኋላ መልእክቱን በራሱ ማጥፋት
    setTimeout(() => {
        if (toast) toast.remove();
    }, 2000);
}

// (የቀሩት የቦርድ እና የኳስ ማሳያ ፈንክሽኖች 'clear75Board'፣ 'updateRecentBallsUI'፣ 'renderMyBoughtCards'፣ ወዘተ እንዳሉ ይቀጥላሉ...)

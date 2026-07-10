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
let isAutoMark = true;

// 🌐 የቴሌግራም ሚኒ አፕ መረጃ መጫኛ
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

        // 🔄 ሪል-ታይም የካርዶች ሁኔታ ማሻሻያ (ማንኛውም ሰው ሲገዛ ለሁሉም እንዲታይ)
        if (data.type === "taken_cards_update") {
            update200CardsColors(data.taken_cards);
        }

        // 1️⃣ PICK PHASE (የሰከንድ እና የደራሽ ስሌት ማሳያ)
        if ((data.type === "countdown" || data.type === "time_update") && data.phase === "PICK") {
            document.getElementById("pickScreen").style.display = "block";
            if(document.getElementById("drawScreen")) document.getElementById("drawScreen").style.display = "none";
            
            const timerText = document.getElementById("timerText");
            if(timerText) {
                timerText.innerText = (data.seconds !== undefined) ? data.seconds : data.time;
            }
            
            // 📊 በፒክ ስክሪን ላይ ያሉትን ጠቋሚዎች በእውነተኛ መረጃ ማደስ
            const statsBoxes = document.querySelectorAll(".stats-grid .stat-box strong");
            if (statsBoxes.length >= 3) {
                if (data.game_no) statsBoxes[0].innerText = data.game_no;
                // የማታለያ ተጫዋች የለም! እውነተኛ ተጫዋቾችን ብቻ ያሳያል
                if (data.player_count !== undefined) statsBoxes[2].innerText = data.player_count;
            }

            // 💰 በዋናው ስክሪን ላይ የደራሽ ባጅ ካለ በእውነተኛው ስሌት ማደስ (ሰው ከሌለ 0 ያደርገዋል)
            const liveDerashBadge = document.querySelector(".derash-badge, #liveDerashBadge");
            if (liveDerashBadge && data.derash !== undefined) {
                liveDerashBadge.innerText = "Derash " + data.derash;
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
            
            // 👥 የማታለያ (Fake Players) ኮድ ሙሉ በሙሉ ተጠርጓል - እውነተኛ መረጃ ብቻ ከባክኤንድ
            const actualDerash = data.derash !== undefined ? data.derash : 0;
            
            if(document.getElementById("stakeAmt")) document.getElementById("stakeAmt").innerText = currentBetAmount;
            if(document.getElementById("derashAmt")) document.getElementById("derashAmt").innerText = actualDerash;
            
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

            // 💰 በኳስ መጣያ ጊዜም የደራሽ መጠን ከተላከ በሪል-ታይም ያድሳል
            if (document.getElementById("derashAmt") && data.derash !== undefined) {
                document.getElementById("derashAmt").innerText = data.derash;
            }
            
            // 🔊 የአማርኛ ድምፅ ማጫወቻ ሎጂክ
            if (soundEnabled) {
                const audio = new Audio(`/static/sounds/${data.number}.mp3`);
                audio.play().catch(e => console.log("🔊 የድምፅ ፋይል አልተገኘም፦", e));
            }

            // 🔴 ኳሱን ወደ ዝርዝር መጨመር
            recentBallsList.unshift({ label: data.label, letter: letter, num: data.number });
            if (recentBallsList.length > 10) recentBallsList.pop();
            updateRecentBallsUI(); 

            // ✅ Auto-Mark የበራ ከሆነ ብቻ በራሱ ያበራል
            if (isAutoMark) {
                const matchingCells = document.querySelectorAll(`.cell-${data.number}`);
                matchingCells.forEach(cell => {
                    cell.classList.add("marked-auto");
                    cell.style.background = color;
                    cell.style.color = "#fff";
                    cell.style.boxShadow = `0 0 12px ${color}`;
                });
            }
        
            if (document.getElementById("callCount")) {
                document.getElementById("callCount").innerText = data.call_count;
            }
        }

        // 4️⃣ GAME OVER - አሸናፊውን ከነ ሙሉ 5x5 ካርዱ ጋር ማሳያ
        if (data.type === "game_over") {
            if (typeof playWinSound === "function") playWinSound();

            const winnerName = data.winner_name || "ተጫዋች";
            const cardNum = data.card_number || "N/A";
            const reason = data.winning_reason || "ቢንጎ";
            const prize = data.prize || 0;
            
            // ከባክኤንድ የመጡት የካርድ ቁጥሮች
            const cardMatrixNumbers = data.card_numbers || []; 
            const winningNumbers = data.winning_numbers || []; 

            // 🎨 የ 5x5 ማትሪክስ ቪዥዋል ዲዛይን መሥሪያ
            let gridHtml = "";
            if (cardMatrixNumbers.length === 25) {
                gridHtml = `<div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 15px auto; max-width: 250px; background: #111; padding: 10px; border-radius: 10px;">`;
                
                cardMatrixNumbers.forEach((num) => {
                    const isWinningNum = winningNumbers.includes(num);
                    const isFreeSpace = num === 0 || num === "★" || num === "FREE";
                    const displayNum = isFreeSpace ? "★" : num;

                    let cellStyle = `
                        aspect-ratio: 1;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-weight: bold;
                        font-size: 14px;
                        border-radius: 6px;
                        transition: all 0.3s;
                    `;

                    if (isWinningNum || isFreeSpace) {
                        // ያሸነፈው መስመር ደምቆ እንዲበራ ✨
                        cellStyle += `background: #ffbc00; color: black; box-shadow: 0 0 12px #ffbc00; border: 1px solid #fff; scale: 1.05;`;
                    } else {
                        // ያልበሩት ቁጥሮች ፈዘዝ ብለው እንዲታዩ
                        cellStyle += `background: #252634; color: #666; border: 1px solid #333;`;
                    }

                    gridHtml += `<div style="${cellStyle}">${displayNum}</div>`;
                });
                
                gridHtml += `</div>`;
            }

            // 📲 ሙሉው የፖፕ-አፕ ስክሪን HTML
            const modalHtml = `
                <div id="winnerModal" style="position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); display:flex; justify-content:center; align-items:center; z-index:9999; color:white; font-family:sans-serif;">
                    <div style="background:#1e1e2e; padding:25px; border-radius:20px; text-align:center; max-width:90%; width:360px; border:2px solid #ffbc00; box-shadow: 0 0 30px rgba(255,188,0,0.3);">
                        
                        <h2 style="color:#ffbc00; margin:0 0 5px 0; font-size:26px; font-weight:900; letter-spacing:1px;">🎉 BINGO! 🎉</h2>
                        <span style="color:#aaa; font-size:13px; display:block;">የአሸናፊው ካርድ ሪፖርት</span>
                        
                        <hr style="border-color:#2a2b3d; margin:15px 0;">
                        
                        <div style="margin:10px 0; font-size:16px; text-align:left; background:#161622; padding:12px; border-radius:10px;">
                            <p style="margin:4px 0;">👤 <b>ስም፦</b> <span style="color:#00ffcc; float:right; font-weight:bold;">${winnerName}</span></p>
                            <p style="margin:4px 0;">🎫 <b>ካርድ፦</b> <span style="color:#ffbc00; float:right; font-weight:bold;">#${cardNum}</span></p>
                            <p style="margin:4px 0;">🏆 <b>የአሸናፊነት ህግ፦</b> <span style="color:#fff; float:right; font-size:13px;">${reason}</span></p>
                        </div>

                        ${gridHtml}

                        <div style="background: rgba(0,255,0,0.1); border: 1px dashed #00ff00; padding: 10px; border-radius: 10px; margin: 15px 0;">
                            <span style="color:#aaa; font-size:13px; display:block;">የተገኘ የገንዘብ መጠን</span>
                            <span style="font-size:26px; color:#00ff00; font-weight:bold;">+${prize} ETB</span>
                        </div>

                        <button onclick="document.getElementById('winnerModal').remove();" style="background:#ffbc00; color:black; border:none; padding:14px; font-size:16px; font-weight:bold; border-radius:10px; cursor:pointer; width:100%; transition:0.2s; box-shadow: 0 4px 10px rgba(255,188,0,0.2);">
                            እሺ (ቀጥል)
                        </button>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // ምርጫዎችን ማጽዳት
            selectedCards = []; 
            temporarilySelectedCards = [];
            document.querySelectorAll(".card-btn").forEach(btn => {
                btn.style.backgroundColor = "#ffffff";
                btn.style.color = "#000000";
                btn.classList.remove("bought", "selected-temp");
            });
        }
    };

    ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

// 🎴 1-200 የካርድ ቁልፎች መፍጠሪያ
function generate200Cards() {
    const grid = document.getElementById("cardGrid");
    if (!grid) return;
    grid.innerHTML = "";
    for (let i = 1; i <= 200; i++) {
        const btn = document.createElement("button");
        btn.className = "card-btn";
        btn.id = `pick-card-${i}`;
        btn.innerText = i;
        btn.style.backgroundColor = "#ffffff";
        btn.style.color = "#000000";
        btn.onclick = () => selectCardTemporarily(i);
        grid.appendChild(btn);
    }
}

// 🎨 የካርድ ቀለማት ማሻሻያ
function update200CardsColors(takenCardsList) {
    for (let i = 1; i <= 200; i++) {
        const btn = document.getElementById(`pick-card-${i}`);
        if (!btn) continue;
        if (temporarilySelectedCards.includes(i)) continue;

        if (takenCardsList.includes(i)) {
            btn.style.backgroundColor = "#ffcc00"; 
            btn.style.color = "#000000";
            btn.classList.add("bought");
        } else {
            btn.style.backgroundColor = "#ffffff"; 
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
        if (btn) {
            btn.classList.remove("selected-temp");
            btn.style.backgroundColor = btn.classList.contains("bought") ? "#ffcc00" : "#ffffff";
            btn.style.color = "#000000";
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
        btn.style.backgroundColor = "#1e90ff"; 
        btn.style.color = "#ffffff";
    }
}

// 🎯 CONFIRM PICKS ሎጂክ
async function confirmAllSelectedPicks() {
    if (temporarilySelectedCards.length === 0) {
        showToastMessage("⚠️ እባክህ መጀመሪያ የሚገዙትን የካርድ ቁጥሮች ይምረጡ!", "error");
        return;
    }

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

            if (result.success === false) {
                showToastMessage("⚠️ " + result.message, "error");
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected-temp");
                    btn.style.backgroundColor = btn.classList.contains("bought") ? "#ffcc00" : "#ffffff";
                    btn.style.color = "#000000";
                }
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                continue; 
            }

            if (result.success === true) {
                selectedCards.push(cardNumber);
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected-temp");
                    btn.classList.add("bought");
                    btn.style.backgroundColor = "#ffcc00"; 
                    btn.style.color = "#000000";
                }

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

function showToastMessage(message, type) {
    const oldToast = document.getElementById("live-toast");
    if (oldToast) oldToast.remove(); 

    const toast = document.createElement("div");
    toast.id = "live-toast";
    let bgColor = type === "success" ? "#2ecc71" : "#e74c3c";
    
    toast.style = `
        position: fixed; top: 20%; left: 50%; transform: translate(-50%, -50%);
        background: ${bgColor}; color: white; padding: 14px 24px; border-radius: 8px;
        font-size: 16px; font-weight: bold; z-index: 9999; text-align: center;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3); transition: opacity 0.3s ease;
    `;
    toast.innerText = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        if (toast) toast.remove();
    }, 2000);
}

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

function updateRecentBallsUI() {
    const recentRow = document.querySelector(".recent-balls-row");
    if (!recentRow) return;
    recentRow.innerHTML = ""; 

    if (recentBallsList.length === 0) {
        recentRow.innerHTML = "<div style='color:#aaa; font-size:12px; text-align:center; width:100%;'>ኳሶች እዚህ ይደረደራሉ...</div>";
        return;
    }
    for (let i = recentBallsList.length - 1; i >= 0; i--) {
        const ball = recentBallsList[i];
        const ballDiv = document.createElement("div");
        ballDiv.className = (i === 0) ? "overlapping-ball current-live-ball" : "overlapping-ball";
        ballDiv.innerHTML = `<span class="b-letter">${ball.letter}</span><span class="b-number">${ball.label.substring(1)}</span>`;
        const color = getBingoColor(ball.letter);
        ballDiv.style.backgroundColor = color;
        ballDiv.style.boxShadow = `0 0 10px ${color}`;
        recentRow.appendChild(ballDiv);
    }
}

async function renderMyBoughtCards() {
    const container = document.getElementById("playerBingoCard");
    if (!container) return;
    container.innerHTML = "";

    if (selectedCards.length === 0) {
        container.innerHTML = "<div style='color:white; text-align:center; padding:20px;'>በዚህ ዙር ምንም ካርድ አልገዙም!</div>";
        return;
    }
    const activeCardNum = selectedCards[currentCardIndex];
    try {
        const res = await fetch(`/api/cards/get_matrix?card_number=${activeCardNum}`);
        const data = await res.json();
        const matrix = data.matrix;

        const mainSliderLayout = document.createElement("div");
        mainSliderLayout.className = "main-slider-layout";

        let html = `
            <button class="side-nav-btn" onclick="moveSlider(-1)">◀</button>
            <div class="card-display-center">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; width: 100%; padding: 0 5px;">
                    <div class="card-title-label" style="color: #ffd700; font-weight: bold; font-size: 13px;">
                        ካርድ #${activeCardNum} (${currentCardIndex + 1}/${selectedCards.length})
                    </div>
                    <button id="toggleMarkBtn" onclick="toggleMarkingMode()" style="background: ${isAutoMark ? '#2ed573' : '#718093'}; color: white; border: none; padding: 4px 8px; font-size: 11px; font-weight: bold; border-radius: 4px; cursor: pointer;">
                        ${isAutoMark ? "🤖 Auto: ON" : "🖐 Manual"}
                    </button>
                </div>
                <div class="bingo-header-letters">
                    <span style="background:${getBingoColor('B')}">B</span>
                    <span style="background:${getBingoColor('I')}">I</span>
                    <span style="background:${getBingoColor('N')}">N</span>
                    <span style="background:${getBingoColor('G')}">G</span>
                    <span style="background:${getBingoColor('O')}">O</span>
                </div>
                <div class="bingo-card-grid-5x5">
        `;

        matrix.forEach(row => {
            row.forEach(cell => {
                if (cell === "FREE") {
                    html += `<div class="bingo-cell free-star">★</div>`;
                } else {
                    const isAlreadyDrawn = recentBallsList.some(b => b.num === cell);
                    
                    if (isAlreadyDrawn && isAutoMark) {
                        let letterPrefix = cell <= 15 ? 'B' : cell <= 30 ? 'I' : cell <= 45 ? 'N' : cell <= 60 ? 'G' : 'O';
                        const savedColor = getBingoColor(letterPrefix);
                        html += `<div class="bingo-cell cell-${cell} marked-auto" style="background:${savedColor} !important; color:#fff;">${cell}</div>`;
                    } else {
                        html += `<div class="bingo-cell cell-${cell}" onclick="handleManualCellClick(this, ${cell})">${cell}</div>`;
                    }
                }
            });
        });
        html += `</div></div><button class="side-nav-btn" onclick="moveSlider(1)">▶</button>`;
        mainSliderLayout.innerHTML = html;
        container.appendChild(mainSliderLayout);
    } catch (e) { console.log(e); }
}

function moveSlider(direction) {
    if (selectedCards.length <= 1) return;
    currentCardIndex += direction;
    if (currentCardIndex < 0) currentCardIndex = selectedCards.length - 1;
    if (currentCardIndex >= selectedCards.length) currentCardIndex = 0;
    renderMyBoughtCards();
}

function showWinnerPopup(message) {
    const popup = document.createElement("div");
    popup.id = "winner-popup";
    popup.style = "position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); display:flex; justify-content:center; align-items:center; z-index:9999; color:white;";
    popup.innerHTML = `
        <div style="background:#2f3542; border:3px solid #ffd700; border-radius:12px; padding:30px; text-align:center; max-width:85%;">
            <h1 style="color:#ffd700; margin-top:0; font-size:28px;">🎉 ቢንጎ ተጠናቀቀ! 🎉</h1>
            <p style="font-size:18px; line-height:1.6; margin:20px 0;">${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" style="background:#ffd700; color:black; border:none; padding:12px 30px; font-size:16px; font-weight:bold; border-radius:6px; cursor:pointer;">Close</button>
        </div>
    `;
    document.body.appendChild(popup);
}

window.onload = () => {
    connectWebSocket();
    const confirmBtn = document.getElementById("confirmBtn");
    if (confirmBtn) confirmBtn.onclick = () => confirmAllSelectedPicks();
};

// 🔄 ሁነታውን መቀያየሪያ
function toggleMarkingMode() {
    isAutoMark = !isAutoMark;
    renderMyBoughtCards(); 
}

// 🖐 በእጅ ቁጥር ሲነካ የሚሰራ ሎጂክ
function handleManualCellClick(cellElement, cellNumber) {
    if (isAutoMark) return;

    const isBallDrawn = recentBallsList.some(b => b.num === cellNumber);

    if (isBallDrawn) {
        let letterPrefix = cellNumber <= 15 ? 'B' : cellNumber <= 30 ? 'I' : cellNumber <= 45 ? 'N' : cellNumber <= 60 ? 'G' : 'O';
        const ballColor = getBingoColor(letterPrefix);
        
        cellElement.style.background = ballColor;
        cellElement.style.color = "#fff";
        cellElement.style.boxShadow = `0 0 10px ${ballColor}`;
        cellElement.classList.add("marked-manual");
    } else {
        const oldBg = cellElement.style.background;
        cellElement.style.background = "#ff4757";
        setTimeout(() => { cellElement.style.background = oldBg; }, 250);
    }
}

// ==========================================================================
// 💳 የኪስ ቦርሳ ፍሰት መቆጣጠሪያ (Wallet Flow - Deposit & Withdraw)
// ==========================================================================

let tgUser = { id: "12345678", first_name: "የይለፍ ተጫዋች" }; 

if (window.Telegram && window.Telegram.WebApp) {
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand(); 
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        tgUser = tg.initDataUnsafe.user;
    }
}

function openWalletModal(type) {
    const modal = document.getElementById('walletModal');
    const title = document.getElementById('modalTitle');
    const depositSec = document.getElementById('depositSection');
    const withdrawSec = document.getElementById('withdrawSection');
    
    modal.style.display = 'flex';
    
    if (type === 'deposit') {
        title.innerText = '💳 ገንዘብ ማስገቢያ (Deposit)';
        depositSec.style.display = 'block';
        withdrawSec.style.display = 'none';
    } else if (type === 'withdraw') {
        title.innerText = '📤 ገንዘብ ማውጫ (Withdraw)';
        depositSec.style.display = 'none';
        withdrawSec.style.display = 'block';
    }
}

function closeWalletModal() {
    document.getElementById('walletModal').style.display = 'none';
}

async function submitDeposit() {
    const amount = parseFloat(document.getElementById('depositAmount').value);
    const bankName = document.getElementById('depositBank').value;
    const smsText = document.getElementById('depositTxn').value.trim();
    
    if (!amount || amount <= 0) {
        alert('እባክዎ መጀመሪያ ትክክለኛ የላኩትን የብር መጠን ያስገቡ!');
        return;
    }
    if (!smsText) {
        alert('እባክዎ የባንኩን SMS እዚህ ሳጥን ላይ ይለጥፉ!');
        return;
    }
    
    const payload = {
        telegram_id: String(myTelegramId), // 👈 ከጨዋታው ግሎባል አይዲ
        telegram_name: String(myTelegramName),
        amount: amount,
        bank_name: bankName,
        sms_data: smsText
    };
    
    try {
        // 🛠 ፊክስ፦ ወደ አዲሱ የ users endpoint መቀየር
        const response = await fetch('/api/users/deposit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ የገንዘብ ማስገቢያ ጥያቄዎ ለአስተዳዳሪው ተልኳል! አድሚኑ መረጃውን አይቶ ሲያጸድቅልዎት ባላንስዎ ላይ ይጨመራል።');
            document.getElementById('depositAmount').value = ''; 
            document.getElementById('depositTxn').value = '';    
            closeWalletModal();
        } else {
            alert('❌ ስህተት፦ ' + result.message);
        }
    } catch (error) {
        console.error('Deposit Error:', error);
        alert('⚠️ ከሰርቨር ጋር መገናኘት አልተቻለም። እባክዎ ትንሽ ቆይተው ይሞክሩ!');
    }
}

async function submitWithdraw() {
    const amount = parseFloat(document.getElementById('withdrawAmount').value);
    const bankName = document.getElementById('withdrawBank').value;
    const accNumber = document.getElementById('withdrawAcc').value.trim();
    
    if (!amount || amount <= 0) {
        alert('እባክዎ ትክክለኛ የብር መጠን ያስገቡ!');
        return;
    }
    if (!accNumber) {
        alert('እባክዎ ብሩ የሚገባበትን አካውንት ወይም ስልክ ቁጥር ያስገቡ!');
        return;
    }
    
    const payload = {
        telegram_id: String(myTelegramId),
        amount: amount,
        bank_name: bankName,
        account_number: accNumber
    };
    
    try {
        // 🛠 ፊክስ፦ ወደ አዲሱ የ users endpoint መቀየር
        const response = await fetch('/api/users/withdraw', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('✅ የማውጫ ጥያቄዎ በተሳካ ሁኔታ ተመዝግቧል። አድሚኑ ብሩን በባንክ ልኮ ሲያጸድቀው መልዕክት ይደርስዎታል!');
            document.getElementById('withdrawAmount').value = '';
            document.getElementById('withdrawAcc').value = '';
            closeWalletModal();
        } else {
            alert('❌ ስህተት፦ ' + result.message);
        }
    } catch (error) {
        console.error('Withdraw Error:', error);
        alert('⚠️ ከሰርቨር ጋር መገናኘት አልተቻለም።');
    }
}

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
function getAmharicLetter(letter) {
    switch (letter) {
        case "B": return "ቢ";
        case "I": return "አይ";
        case "N": return "ኤን";
        case "G": return "ጂ";
        case "O": return "ኦ";
        default: return "";
    }
}

const amharicNumbers = {
1:"አንድ",
2:"ሁለት",
3:"ሶስት",
4:"አራት",
5:"አምስት",
6:"ስድስት",
7:"ሰባት",
8:"ስምንት",
9:"ዘጠኝ",
10:"አስር",
11:"አስራ አንድ",
12:"አስራ ሁለት",
13:"አስራ ሶስት",
14:"አስራ አራት",
15:"አስራ አምስት",
16:"አስራ ስድስት",
17:"አስራ ሰባት",
18:"አስራ ስምንት",
19:"አስራ ዘጠኝ",
20:"ሃያ",
21:"ሃያ አንድ",
22:"ሃያ ሁለት",
23:"ሃያ ሶስት",
24:"ሃያ አራት",
25:"ሃያ አምስት",
26:"ሃያ ስድስት",
27:"ሃያ ሰባት",
28:"ሃያ ስምንት",
29:"ሃያ ዘጠኝ",
30:"ሠላሳ",
31:"ሠላሳ አንድ",
32:"ሠላሳ ሁለት",
33:"ሠላሳ ሶስት",
34:"ሠላሳ አራት",
35:"ሠላሳ አምስት",
36:"ሠላሳ ስድስት",
37:"ሠላሳ ሰባት",
38:"ሠላሳ ስምንት",
39:"ሠላሳ ዘጠኝ",
40:"አርባ",
41:"አርባ አንድ",
42:"አርባ ሁለት",
43:"አርባ ሶስት",
44:"አርባ አራት",
45:"አርባ አምስት",
46:"አርባ ስድስት",
47:"አርባ ሰባት",
48:"አርባ ስምንት",
49:"አርባ ዘጠኝ",
50:"ሀምሳ",  
51:"ሀምሳ አንድ",
52:"ሀምሳ ሁለት",
53:"ሀምሳ ሶስት",
54:"ሀምሳ አራት",
55:"ሀምሳ አምስት",
56:"ሀምሳ ስድስት",
57:"ሀምሳ ሰባት",
58:"ሀምሳ ስምንት",
59:"ሀምሳ ዘጠኝ",
60:"ስልሳ",
61:"ስልሳ አንድ",
62:"ስልሳ ሁለት",
63:"ስልሳ ሶስት",
64:"ስልሳ አራት",
65:"ስልሳ አምስት",
66:"ስልሳ ስድስት",
67:"ስልሳ ሰባት",
68:"ስልሳ ስምንት",
69:"ስልሳ ዘጠኝ",
70:"ሰባ",
71:"ሰባ አንድ",
72:"ሰባ ሁለት",
73:"ሰባ ሶስት",
74:"ሰባ አራት",
75:"ሰባ አምስት"    
};

function playBallSound(ballLabel) {

    if (!soundEnabled) return;

    speechSynthesis.cancel();

    const letter = ballLabel.charAt(0);
    const number = parseInt(ballLabel.substring(1));

    const speakText =
        getAmharicLetter(letter) + " " +
        (amharicNumbers[number] || number);

    const speech = new SpeechSynthesisUtterance(speakText);

    speech.lang = "am-ET";
    speech.rate = 0.8;
    speech.pitch = 1;

    speechSynthesis.speak(speech);
}

function toggleSound() {

    soundEnabled = !soundEnabled;

    const btn = document.getElementById("soundBtn");

    if (btn) {
        btn.innerHTML = soundEnabled ? "🔊" : "🔇";
    }

    if (!soundEnabled) {
        speechSynthesis.cancel();
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

            // 1-75 ሰሌዳ ላይ ቁጥሩን በፊደሉ ቀለም ማብራት
            const ballElement = document.getElementById(`ball-${data.number}`);
            const letter = data.label.charAt(0);
            const color = getBingoColor(letter);
            
            if (ballElement) {
                ballElement.classList.add("drawn");
                ballElement.style.background = color;
                ballElement.style.color = "#fff";
                ballElement.style.boxShadow = `0 0 10px ${color}`;
            }

            playBallSound(data.label);

            // 🔴 ኳሱን ወደ ዝርዝር መጨመር
            recentBallsList.unshift({ label: data.label, letter: letter, num: data.number });
            if (recentBallsList.length > 10) recentBallsList.pop();
            updateRecentBallsUI(); 

            // AUTO MARKING - ልክ በምስሉ እንዳለው በፊደሉ ቀለም ማብራት
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
            
            document.querySelectorAll(".card-btn").forEach(btn => {
                btn.classList.remove("bought", "selected-temp");
            });
        }
    };

    ws.onclose = () => setTimeout(connectWebSocket, 2000);
}

// 🎴 1-200 የካርድ መምረጫ አዝራሮች
function generate200Cards() {
    const grid = document.getElementById("cardGrid");
    if (!grid) return;
    grid.innerHTML = "";
    for (let i = 1; i <= 200; i++) {
        const btn = document.createElement("button");
        btn.className = "card-btn";
        btn.id = `pick-card-${i}`;
        btn.innerText = i;
        btn.onclick = () => selectCardTemporarily(i);
        grid.appendChild(btn);
    }
}

function selectCardTemporarily(cardNumber) {
    const btn = document.getElementById(`pick-card-${cardNumber}`);
    if (selectedCards.includes(cardNumber)) return;

    if (temporarilySelectedCards.includes(cardNumber)) {
        temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
        if (btn) btn.classList.remove("selected-temp");
        return;
    }

    if (temporarilySelectedCards.length + selectedCards.length >= 5) {
        alert("በአንድ ጨዋታ መግዛት የሚችሉት ከፍተኛው የካርድ መጠን 5 ብቻ ነው!");
        return;
    }

    temporarilySelectedCards.push(cardNumber);
    if (btn) btn.classList.add("selected-temp");
}

async function confirmAllSelectedPicks() {
    if (temporarilySelectedCards.length === 0) {
        alert("እባክህ መጀመሪያ የሚገዙትን የካርድ ቁጥሮች ይምረጡ!");
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

            if (result.success) {
                selectedCards.push(cardNumber);
                temporarilySelectedCards = temporarilySelectedCards.filter(id => id !== cardNumber);
                
                const btn = document.getElementById(`pick-card-${cardNumber}`);
                if (btn) {
                    btn.classList.remove("selected-temp");
                    btn.classList.add("bought");
                }

                const statsBoxes = document.querySelectorAll(".stats-grid .stat-box strong");
                if (statsBoxes.length >= 4) {
                    statsBoxes[3].innerText = result.current_balance + " ETB";
                }
            }
        } catch (e) {
            console.log(e);
        }
    }
    alert("የመረጧቸው ካርዶች በተሳካ ሁኔታ ተገዝተዋል!");
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

// 🔴 [ማሻሻያ] ልክ በምስሉ ላይ እንዳለው ኳሶችን በክብ አድርጎ ደራራቢ የማድረጊያ ሎጂክ
function updateRecentBallsUI() {
    const recentRow = document.querySelector(".recent-balls-row");
    if (!recentRow) return;
    recentRow.innerHTML = ""; 

    if (recentBallsList.length === 0) {
        recentRow.innerHTML = "<div style='color:#aaa; font-size:12px; text-align:center; width:100%;'>ኳሶች እዚህ ይደረደራሉ...</div>";
        return;
    }

    // ከበስተጀርባ ያሉት ኳሶች ወደ ቀኝ እንዲሄዱና አዲሱ ኳስ (index 0) ከፊት እንዲሆን ከበስተኋላ ጀምረን እንስላለን
    for (let i = recentBallsList.length - 1; i >= 0; i--) {
        const ball = recentBallsList[i];
        const ballDiv = document.createElement("div");
        
        // i == 0 ማለት አሁን የወረደው ዋነኛው ትልቅ ኳስ ነው
        ballDiv.className = (i === 0) ? "overlapping-ball current-live-ball" : "overlapping-ball";
        
        // የኳሱ መለያ ፊደል እና ቁጥር (ለምሳሌ N36)
        ballDiv.innerHTML = `<span class="b-letter">${ball.letter}</span><span class="b-number">${ball.label.substring(1)}</span>`;
        
        // ቀለማቸውን ማመሳሰል
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
                <div class="card-title-label" style="color: #ffd700; font-weight: bold; margin-bottom: 6px; font-size: 13px;">
                    ካርድ #${activeCardNum} (${currentCardIndex + 1}/${selectedCards.length})
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
                    if (isAlreadyDrawn) {
                        let letterPrefix = '';
                        if (cell <= 15) letterPrefix = 'B';
                        else if (cell <= 30) letterPrefix = 'I';
                        else if (cell <= 45) letterPrefix = 'N';
                        else if (cell <= 60) letterPrefix = 'G';
                        else letterPrefix = 'O';
                        
                        const savedColor = getBingoColor(letterPrefix);
                        html += `
                            <div class="bingo-cell cell-${cell} marked-auto" style="background:${savedColor} !important; color:#fff; box-shadow: 0 0 10px ${savedColor}; border-color: #fff;">
                                ${cell}
                            </div>`;
                    } else {
                        html += `
                            <div class="bingo-cell cell-${cell}" onclick="this.classList.toggle('marked-manual')">
                                ${cell}
                            </div>`;
                    }
                }
            });
        });

        html += `
                </div>
            </div>
            
            <button class="side-nav-btn" onclick="moveSlider(1)">▶</button>
        `;

        mainSliderLayout.innerHTML = html;
        container.appendChild(mainSliderLayout);

    } catch (e) {
        console.log("ስህተት፦", e);
    }
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
            <button onclick="this.parentElement.parentElement.remove()" style="background:#ffd700; color:black; border:none; padding:12px 30px; font-size:16px; font-weight:bold; border-radius:6px; cursor:pointer;">እሺ</button>
        </div>
    `;
    document.body.appendChild(popup);
}

window.onload = () => {
    connectWebSocket();
    const confirmBtn = document.getElementById("confirmBtn");
    if (confirmBtn) confirmBtn.onclick = () => confirmAllSelectedPicks();
};

const timerText = document.getElementById("timer");

let selected = [];
let seconds = 30;

// Demo player info
document.getElementById("username").innerText = "Test Player";
document.getElementById("balance").innerText = "0 ETB";

// ----------------------------
// Pick System
// ----------------------------

let selectedCard = null;
let pickedCount = 0;

const grid = document.getElementById("cardGrid");

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

document.getElementById("confirmBtn").onclick = async () => {

    if (selectedCard == null){

        alert("Select one card first.");

        return;

    }

    if(pickedCount >= 5){

        alert("Maximum 5 cards reached.");

        return;

    }

    const response = await fetch("/api/cards/pick", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        telegram_id: telegramId,
        card_number: selectedCard
    })
});

const result = await response.json();

if(result.success){

    pickedCount++;

    document
        .querySelector(`[data-number="${selectedCard}"]`)
        .classList.remove("selected");

    document
        .querySelector(`[data-number="${selectedCard}"]`)
        .classList.add("taken");

    alert(
        `Card ${selectedCard} reserved (${pickedCount}/5)`
    );

    selectedCard = null;

}else{

    alert(result.message);

}

// Timer
const timer = setInterval(() => {

    seconds--;

    timerText.innerText = seconds;

    if (seconds <= 0) {

        clearInterval(timer);

        document.getElementById("confirmBtn").disabled = true;

        document.getElementById("pickSection").style.display = "none";

        document.getElementById("bingoSection").style.display = "block";

        // ከጊዜያዊ demo card ጋር እየሞከርን ነው
        renderPlayerCard(demoCard);

    }

},1000);


// =============================
// Create Bingo Board (1-75)
// =============================

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
    
// ==========================
// WebSocket Connection
// ==========================

const protocol = location.protocol === "https:" ? "wss" : "ws";

const socket = new WebSocket(
    protocol + "://" + location.host + "/ws"
);

let callCount = 0;

socket.onmessage = function(event){

    const data = JSON.parse(event.data);

    if(data.type !== "ball") return;

    callCount++;

    document.getElementById("callCount").innerText = callCount;

    document
        .getElementById("ball-" + data.number)
        ?.classList.add("called");

};

// =========================
// Render Player Bingo Card
// =========================

function renderPlayerCard(card){

    const board = document.getElementById("playerCard");

    board.innerHTML = "";

    card.forEach(row=>{

        row.forEach(value=>{

            const cell=document.createElement("div");

            cell.className="cell";

            if(value==="FREE"){

                cell.classList.add("free");

                cell.innerHTML="★";

            }else{

                cell.innerHTML=value;

            }

            board.appendChild(cell);

        });

    });

}
    
const demoCard=[

[4,25,37,51,61],

[7,16,35,60,72],

[5,20,"FREE",57,73],

[14,17,39,48,75],

[3,24,45,50,71]

];

renderPlayerCard(demoCard);

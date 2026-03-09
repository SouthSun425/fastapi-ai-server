document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("access_token");
    const userInfo = document.getElementById("user-info");
    const usageInfo = document.getElementById("usage-info");
    const message = document.getElementById("message");
    const resultText = document.getElementById("result-text");
    const sttForm = document.getElementById("stt-form");
    const loadUsageBtn = document.getElementById("load-usage-btn");
    const logoutBtn = document.getElementById("logout-btn");

    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = "/login-page";
        return;
    }

    async function loadMe() {
        try {
            const response = await fetch("/me", {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const data = await response.json();

            if (!response.ok) {
                alert(data.detail || "사용자 정보 조회 실패");
                window.location.href = "/login-page";
                return;
            }

            userInfo.textContent = `로그인 사용자: ${data.email}`;
        } catch (error) {
            userInfo.textContent = "사용자 정보를 불러오지 못했습니다.";
        }
    }

    async function loadUsage() {
        try {
            const response = await fetch("/my/usage/today", {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const data = await response.json();

            if (!response.ok) {
                usageInfo.textContent = data.detail || "사용량 조회 실패";
                return;
            }

            usageInfo.textContent =
                `오늘 사용량: ${data.today_usage_count} / 제한: ${data.is_unlimited ? "무제한" : data.daily_limit}`;
        } catch (error) {
            usageInfo.textContent = "사용량 조회 중 오류가 발생했습니다.";
        }
    }

    sttForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const fileInput = document.getElementById("audio-file");
        const file = fileInput.files[0];

        if (!file) {
            message.textContent = "음성 파일을 선택하세요.";
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        message.textContent = "변환 중...";
        resultText.textContent = "음성을 분석하고 있습니다...";

        try {
            const response = await fetch("/stt", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                message.textContent = data.detail || "STT 변환 실패";
                resultText.textContent = "변환에 실패했습니다.";
                return;
            }

            message.textContent = "STT 변환 완료";
            resultText.textContent = data.text || "변환 결과가 없습니다.";
            loadUsage();
        } catch (error) {
            message.textContent = "서버 요청 중 오류가 발생했습니다.";
            resultText.textContent = "변환 중 오류가 발생했습니다.";
        }
    });

    loadUsageBtn.addEventListener("click", function () {
        loadUsage();
    });

    if (logoutBtn) {
        logoutBtn.addEventListener("click", function () {
            localStorage.removeItem("access_token");
            localStorage.removeItem("user_email");
            localStorage.removeItem("is_admin");
            window.location.href = "/login-page";
        });
    }

    loadMe();
    loadUsage();
});
document.addEventListener("DOMContentLoaded", function () {
    const loginBtn = document.getElementById("login-btn");
    const message = document.getElementById("message");

    if (!loginBtn) {
        console.log("login button not found");
        return;
    }

    loginBtn.addEventListener("click", async function () {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        if (!email || !password) {
            message.textContent = "이메일과 비밀번호를 입력하세요.";
            return;
        }

        message.textContent = "로그인 요청 중...";

        try {
            const response = await fetch("/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    email: email,
                    password: password
                })
            });

            const data = await response.json();

            if (!response.ok) {
                message.textContent = data.detail || "로그인 실패";
                return;
            }

            localStorage.setItem("access_token", data.access_token);
            localStorage.setItem("user_email", data.email);
            localStorage.setItem("is_admin", String(data.is_admin));

            message.textContent = "로그인 성공";

            if (data.is_admin) {
                window.location.href = "/admin-page";
            } else {
                window.location.href = "/stt-page";
            }
        } catch (error) {
            console.error("login error:", error);
            message.textContent = "서버 요청 중 오류가 발생했습니다.";
        }
    });
});
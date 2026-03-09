document.addEventListener("DOMContentLoaded", function () {
    const signupBtn = document.getElementById("signup-btn");
    const message = document.getElementById("message");

    if (!signupBtn) {
        console.log("signup button not found");
        return;
    }

    signupBtn.addEventListener("click", async function () {
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        if (!email || !password) {
            message.textContent = "이메일과 비밀번호를 입력하세요.";
            return;
        }

        signupBtn.disabled = true;
        message.textContent = "회원가입 요청 중...";

        try {
            const response = await fetch("/signup", {
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
                message.textContent = data.detail || "회원가입 실패";
                signupBtn.disabled = false;
                return;
            }

            message.textContent = "회원가입 성공. 로그인 페이지로 이동합니다.";

            setTimeout(function () {
                window.location.href = "/login-page";
            }, 1000);
        } catch (error) {
            console.error("signup error:", error);
            message.textContent = "서버 요청 중 오류가 발생했습니다.";
            signupBtn.disabled = false;
        }
    });
});
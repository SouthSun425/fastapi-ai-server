document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem("access_token");
    const adminInfo = document.getElementById("admin-info");
    const usersContainer = document.getElementById("users-container");
    const usageContainer = document.getElementById("usage-container");
    const message = document.getElementById("message");
    const loadUsersBtn = document.getElementById("load-users-btn");
    const loadUsageBtn = document.getElementById("load-usage-btn");
    const logoutBtn = document.getElementById("logout-btn");

    if (!token) {
        alert("로그인이 필요합니다.");
        window.location.href = "/login-page";
        return;
    }

    function badge(text, className) {
        return `<span class="badge ${className}">${text}</span>`;
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

            if (!data.is_admin) {
                alert("관리자 권한이 없습니다.");
                window.location.href = "/stt-page";
                return;
            }

            adminInfo.textContent = `관리자: ${data.email}`;
        } catch (error) {
            adminInfo.textContent = "관리자 정보를 불러오지 못했습니다.";
        }
    }

    async function loadUsers() {
        usersContainer.innerHTML = "불러오는 중...";

        try {
            const response = await fetch("/admin/users", {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const data = await response.json();

            if (!response.ok) {
                usersContainer.innerHTML = data.detail || "사용자 목록 조회 실패";
                return;
            }

            if (!Array.isArray(data) || data.length === 0) {
                usersContainer.innerHTML = "사용자가 없습니다.";
                return;
            }

            let html = `
                <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>이메일</th>
                            <th>권한</th>
                            <th>계정 상태</th>
                            <th>STT 상태</th>
                            <th>사용 정책</th>
                            <th>일일 제한</th>
                            <th>작업</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            for (const user of data) {
                html += `
                    <tr>
                        <td>${user.id}</td>
                        <td>${user.email}</td>
                        <td>${user.is_admin ? badge("관리자", "badge-admin") : badge("일반", "badge-user")}</td>
                        <td>${user.is_active ? badge("활성", "badge-active") : badge("비활성", "badge-inactive")}</td>
                        <td>${user.can_use_stt ? badge("사용 가능", "badge-enabled") : badge("차단", "badge-disabled")}</td>
                        <td>${user.is_unlimited ? badge("무제한", "badge-unlimited") : badge("제한", "badge-limited")}</td>
                        <td>${user.daily_limit}</td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn-enable" onclick="enableUser('${user.email}')">승인</button>
                                <button class="btn-disable" onclick="disableUser('${user.email}')">차단</button>
                                <button class="btn-unlimited" onclick="setUnlimitedUser('${user.email}')">무제한</button>
                                <button class="btn-limited" onclick="setLimitedUser('${user.email}')">제한설정</button>
                            </div>
                        </td>
                    </tr>
                `;
            }

            html += `
                    </tbody>
                </table>
            `;

            usersContainer.innerHTML = html;
        } catch (error) {
            usersContainer.innerHTML = "사용자 목록 조회 중 오류가 발생했습니다.";
        }
    }

    async function loadUsage() {
        usageContainer.innerHTML = "불러오는 중...";

        try {
            const response = await fetch("/admin/usage/today", {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const data = await response.json();

            if (!response.ok) {
                usageContainer.innerHTML = data.detail || "사용량 조회 실패";
                return;
            }

            if (!Array.isArray(data) || data.length === 0) {
                usageContainer.innerHTML = "사용량 데이터가 없습니다.";
                return;
            }

            let html = `
                <table>
                    <thead>
                        <tr>
                            <th>이메일</th>
                            <th>오늘 사용량</th>
                            <th>일일 제한</th>
                            <th>사용 정책</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            for (const item of data) {
                html += `
                    <tr>
                        <td>${item.email}</td>
                        <td>${item.today_usage_count}</td>
                        <td>${item.daily_limit}</td>
                        <td>${item.is_unlimited ? badge("무제한", "badge-unlimited") : badge("제한", "badge-limited")}</td>
                    </tr>
                `;
            }

            html += `
                    </tbody>
                </table>
            `;

            usageContainer.innerHTML = html;
        } catch (error) {
            usageContainer.innerHTML = "사용량 조회 중 오류가 발생했습니다.";
        }
    }

    async function postJson(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });

        const data = await response.json();
        return { response, data };
    }

    window.enableUser = async function (email) {
        try {
            const { response, data } = await postJson("/admin/users/enable", { email });

            if (!response.ok) {
                message.textContent = data.detail || "승인 실패";
                return;
            }

            message.textContent = `${email} 사용자 승인 완료`;
            loadUsers();
        } catch (error) {
            message.textContent = "승인 처리 중 오류가 발생했습니다.";
        }
    };

    window.disableUser = async function (email) {
        try {
            const { response, data } = await postJson("/admin/users/disable", { email });

            if (!response.ok) {
                message.textContent = data.detail || "차단 실패";
                return;
            }

            message.textContent = `${email} 사용자 차단 완료`;
            loadUsers();
        } catch (error) {
            message.textContent = "차단 처리 중 오류가 발생했습니다.";
        }
    };

    window.setUnlimitedUser = async function (email) {
        try {
            const { response, data } = await postJson("/admin/users/set-unlimited", { email });

            if (!response.ok) {
                message.textContent = data.detail || "무제한 설정 실패";
                return;
            }

            message.textContent = `${email} 무제한 설정 완료`;
            loadUsers();
        } catch (error) {
            message.textContent = "무제한 설정 중 오류가 발생했습니다.";
        }
    };

    window.setLimitedUser = async function (email) {
        const dailyLimit = prompt("일일 제한 횟수를 입력하세요.", "10");

        if (!dailyLimit) {
            return;
        }

        try {
            const { response, data } = await postJson("/admin/users/set-limited", {
                email,
                daily_limit: Number(dailyLimit)
            });

            if (!response.ok) {
                message.textContent = data.detail || "제한 설정 실패";
                return;
            }

            message.textContent = `${email} 제한 계정 설정 완료`;
            loadUsers();
        } catch (error) {
            message.textContent = "제한 설정 중 오류가 발생했습니다.";
        }
    };

    loadUsersBtn.addEventListener("click", function () {
        loadUsers();
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
    loadUsers();
});
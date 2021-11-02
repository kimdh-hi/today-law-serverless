$(document).ready(function () {
    Kakao.init('c57fd548872ef2dc73b41ecd5e45836e');
})

function show_login_modal() {
    tmp_html = `<div class="modal is-active">
                                <div class="modal-background" onclick="close_modal()"></div>
                                <div class="modal-content" style="width: 500px; height: 360px; margin: auto;">

                                        <div class="card-content" style="text-align: center">     
                                        <p style="font-size: 30px">로그인</p>                             
                                            <div class="content" style="margin-top: 40px">
                                                <ul class="social_button">
                                                    <li>
                                                        <button class="img_kakao" onclick="getKakaoAccessToken()"></button>
                                                    </li>
                                                    <li>
                                                        <button class="img_google" onclick="window.location.href='/oauth/google'"></button>
                                                    </li>
                                                    <li>
                                                        <button class="img_naver" onclick="window.location.href='/oauth/naver'"></button>
                                                    </li>
                                                </ul>                                                
                                            </div>

                                        </div>

                                </div>
                                <button class="modal-close is-large" aria-label="close" onclick="close_modal()"></button>
                            </div>`
    $('body').append(tmp_html)
}

function getKakaoAccessToken() {
    Kakao.Auth.login({
        success: function(response) {
            accessToken = response['access_token']
            kakaoLogin(accessToken)
        }, fail: function(error) {
            console.log(error)
        }
    })
}

function kakaoLogin(accessToken) {
    $.ajax({
        type: "POST",
        url: `${api_url}/kakao-login`,
        data: JSON.stringify({accessToken: accessToken}),
        success: function (res) {
            if (res['result'] === 'success') {
                alert('로그인에 성공했습니다.')
                localStorage.setItem("token", res['token'])
                window.location.reload()
            } else {
                alert('로그인에 실패했습니다.')
                window.location.reload()
            }
        }
    })
}

function close_modal() {
    $(".modal").removeClass("is-active");
    $(".modal").empty();
}


function logout() {
    localStorage.removeItem("token")
    alert('로그아웃')
    window.location.reload()
}



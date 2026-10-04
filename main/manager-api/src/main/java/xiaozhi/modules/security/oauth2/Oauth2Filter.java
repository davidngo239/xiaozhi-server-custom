package xiaozhi.modules.security.oauth2;

import java.io.IOException;

import org.apache.commons.lang3.StringUtils;
import org.apache.shiro.authc.AuthenticationException;
import org.apache.shiro.authc.AuthenticationToken;
import org.apache.shiro.web.filter.authc.AuthenticatingFilter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.RequestMethod;

import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.utils.HttpContextUtils;
import xiaozhi.common.utils.JsonUtils;
import xiaozhi.common.utils.MessageUtils;
import xiaozhi.common.utils.Result;

/**
 * bộ lọc oauth2
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class Oauth2Filter extends AuthenticatingFilter {

    private static final Logger logger = LoggerFactory.getLogger(Oauth2Filter.class);

    @Override
    protected AuthenticationToken createToken(ServletRequest request, ServletResponse response) throws Exception {
        // Nhận mã thông báo yêu cầu
        String token = getRequestToken((HttpServletRequest) request);

        if (StringUtils.isBlank(token)) {
            logger.warn("createToken:token is empty");
            return null;
        }

        return new Oauth2Token(token);
    }

    @Override
    protected boolean isAccessAllowed(ServletRequest request, ServletResponse response, Object mappedValue) {
        if (((HttpServletRequest) request).getMethod().equals(RequestMethod.OPTIONS.name())) {
            return true;
        }

        return false;
    }

    @Override
    protected boolean onAccessDenied(ServletRequest request, ServletResponse response) throws Exception {
        // Nhận mã thông báo yêu cầu. Nếu mã thông báo không tồn tại, hãy trả lại trực tiếp 401.
        String token = getRequestToken((HttpServletRequest) request);

        if (StringUtils.isBlank(token)) {
            logger.warn("onAccessDenied:token is empty");

            HttpServletResponse httpResponse = (HttpServletResponse) response;
            httpResponse.setContentType("application/json;charset=utf-8");
            httpResponse.setHeader("Access-Control-Allow-Credentials", "true");
            httpResponse.setHeader("Access-Control-Allow-Origin", HttpContextUtils.getOrigin());

            String json = JsonUtils.toJsonString(new Result<Void>().error(ErrorCode.UNAUTHORIZED));

            httpResponse.getWriter().print(json);

            return false;
        }

        return executeLogin(request, response);
    }

    @Override
    protected boolean onLoginFailure(AuthenticationToken token, AuthenticationException e, ServletRequest request,
            ServletResponse response) {
        HttpServletResponse httpResponse = (HttpServletResponse) response;
        httpResponse.setContentType("application/json;charset=utf-8");
        httpResponse.setHeader("Access-Control-Allow-Credentials", "true");
        httpResponse.setHeader("Access-Control-Allow-Origin", HttpContextUtils.getOrigin());
        try {
            // Sử dụng tin nhắn được quốc tế hóa thay vì sử dụng trực tiếp tin nhắn ngoại lệ
            Result<Void> r = new Result<Void>().error(ErrorCode.UNAUTHORIZED);

            String json = JsonUtils.toJsonString(r);
            httpResponse.getWriter().print(json);
        } catch (IOException e1) {
        }

        return false;
    }

    /**
     * Nhận mã thông báo được yêu cầu
     */
    private String getRequestToken(HttpServletRequest httpRequest) {
        String token = null;
        // Nhận mã thông báo từ tiêu đề
        String authorization = httpRequest.getHeader(Constant.AUTHORIZATION);
        if (StringUtils.isNotBlank(authorization) && authorization.startsWith("Bearer ")) {
            token = authorization.replace("Bearer ", "");
        }
        return token;
    }
}
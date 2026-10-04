package xiaozhi.modules.security.secret;

import org.apache.shiro.authc.AuthenticationToken;

/**
 * Mã thông báo API cấu hình
 */
public class ServerSecretToken implements AuthenticationToken {
    private static final long serialVersionUID = 1L;
    private final String token;

    public ServerSecretToken(String token) {
        this.token = token;
    }

    @Override
    public Object getPrincipal() {
        return token;
    }

    @Override
    public Object getCredentials() {
        return token;
    }
} 

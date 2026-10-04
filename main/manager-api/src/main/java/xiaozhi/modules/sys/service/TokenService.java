package xiaozhi.modules.sys.service;

public interface TokenService {
    /**
     * Tạo mã thông báo
     *
     * @param userId
     * @return
     */
    String createToken(long userId);
}

package xiaozhi.modules.security.service.impl;

import java.util.Date;

import org.springframework.stereotype.Service;

import cn.hutool.core.date.DateUtil;
import lombok.AllArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.TokenDTO;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.common.utils.HttpContextUtils;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.security.dao.SysUserTokenDao;
import xiaozhi.modules.security.entity.SysUserTokenEntity;
import xiaozhi.modules.security.oauth2.TokenGenerator;
import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.sys.dto.PasswordDTO;
import xiaozhi.modules.sys.dto.SysUserDTO;
import xiaozhi.modules.sys.service.SysUserService;

@AllArgsConstructor
@Service
public class SysUserTokenServiceImpl extends BaseServiceImpl<SysUserTokenDao, SysUserTokenEntity>
        implements SysUserTokenService {

    private final SysUserService sysUserService;
    /**
     * Hết hạn sau 12 giờ
     */
    private final static int EXPIRE = 3600 * 12;

    @Override
    public Result<TokenDTO> createToken(Long userId) {
        // mã thông báo người dùng
        String token;

        // thời điểm hiện tại
        Date now = new Date();
        // Thời gian hết hạn
        Date expireTime = new Date(now.getTime() + EXPIRE * 1000);

        // Xác định xem mã thông báo đã được tạo chưa
        SysUserTokenEntity tokenEntity = baseDao.getByUserId(userId);
        if (tokenEntity == null) {
            // Tạo mã thông báo
            token = TokenGenerator.generateValue();

            tokenEntity = new SysUserTokenEntity();
            tokenEntity.setUserId(userId);
            tokenEntity.setToken(token);
            tokenEntity.setUpdateDate(now);
            tokenEntity.setExpireDate(expireTime);

            // lưu mã thông báo
            this.insert(tokenEntity);
        } else {
            // Xác định xem mã thông báo đã hết hạn chưa
            if (tokenEntity.getExpireDate().getTime() < System.currentTimeMillis()) {
                // Mã thông báo hết hạn, hãy tạo lại mã thông báo
                token = TokenGenerator.generateValue();
            } else {
                token = tokenEntity.getToken();
            }

            tokenEntity.setToken(token);
            tokenEntity.setUpdateDate(now);
            tokenEntity.setExpireDate(expireTime);

            // mã thông báo cập nhật
            this.updateById(tokenEntity);
        }

        String clientHash = HttpContextUtils.getClientCode();

        TokenDTO tokenDTO = new TokenDTO();
        tokenDTO.setToken(token);
        tokenDTO.setExpire(EXPIRE);
        tokenDTO.setClientHash(clientHash);
        return new Result<TokenDTO>().ok(tokenDTO);
    }

    @Override
    public SysUserDTO getUserByToken(String token) {
        SysUserTokenEntity userToken = baseDao.getByToken(token);
        if (null == userToken) {
            throw new RenException(ErrorCode.TOKEN_INVALID);
        }

        Date now = new Date();
        if (userToken.getExpireDate().before(now)) {
            throw new RenException(ErrorCode.UNAUTHORIZED);
        }

        SysUserDTO userDTO = sysUserService.getByUserId(userToken.getUserId());
        userDTO.setPassword("");
        return userDTO;
    }

    @Override
    public void logout(Long userId) {
        Date expireDate = DateUtil.offsetMinute(new Date(), -1);
        baseDao.logout(userId, expireDate);
    }

    @Override
    public void changePassword(Long userId, PasswordDTO passwordDTO) {
        // Thay đổi mật khẩu
        sysUserService.changePassword(userId, passwordDTO);

        // Vô hiệu hóa mã thông báo và bạn sẽ cần phải đăng nhập lại
        Date expireDate = DateUtil.offsetMinute(new Date(), -1);
        baseDao.logout(userId, expireDate);
    }
}
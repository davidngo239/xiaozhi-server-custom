package xiaozhi.common.utils;

import org.apache.commons.lang3.StringUtils;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.modules.security.service.CaptchaService;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * Lớp công cụ xác minh mã xác minh và giải mã SM2
 * Đóng gói giải mã SM2 lặp đi lặp lại, trích xuất mã xác minh và logic xác minh
 */
public class Sm2DecryptUtil {

    /**
     * Độ dài mã xác minh
     */
    private static final int CAPTCHA_LENGTH = 5;

    /**
     * Giải mã nội dung mã hóa SM2, trích xuất mã xác minh và xác minh
     * 
     * @param encryptedPassword hóa Chuỗi mật khẩu được mã hóa SM2
     * @param captchaId mã xác minh captchaId
     * @param captchaService vụ mã xác minh captchaService
     * @param sysParamsService dịch vụ tham số hệ thống
     * @trả lại mật khẩu thực tế sau khi giải mã
     */
    public static String decryptAndValidateCaptcha(String encryptedPassword, String captchaId,
            CaptchaService captchaService, SysParamsService sysParamsService) {
        // Nhận khóa riêng SM2
        String privateKeyStr = sysParamsService.getValue(Constant.SM2_PRIVATE_KEY, true);
        if (StringUtils.isBlank(privateKeyStr)) {
            throw new RenException(ErrorCode.SM2_KEY_NOT_CONFIGURED);
        }

        // Giải mã mật khẩu bằng khóa riêng SM2
        String decryptedContent;
        try {
            decryptedContent = SM2Utils.decrypt(privateKeyStr, encryptedPassword);
        } catch (Exception e) {
            throw new RenException(ErrorCode.SM2_DECRYPT_ERROR);
        }

        // Tách biệt mã xác thực và mật khẩu: 5 chữ số đầu tiên là mã xác minh, tiếp theo là mật khẩu
        if (decryptedContent.length() > CAPTCHA_LENGTH) {
            String embeddedCaptcha = decryptedContent.substring(0, CAPTCHA_LENGTH);
            String actualPassword = decryptedContent.substring(CAPTCHA_LENGTH);

            boolean embeddedCaptchaValid = captchaService.validate(captchaId, embeddedCaptcha, true);
            if (!embeddedCaptchaValid) {
                throw new RenException(ErrorCode.SMS_CAPTCHA_ERROR);
            }

            return actualPassword;
        } else if (decryptedContent.length() > 0) {
            throw new RenException(ErrorCode.SMS_CAPTCHA_ERROR);
        } else {
            throw new RenException(ErrorCode.SM2_DECRYPT_ERROR);
        }
    }
}
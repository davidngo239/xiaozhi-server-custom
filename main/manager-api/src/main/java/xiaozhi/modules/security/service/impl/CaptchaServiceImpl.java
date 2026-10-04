package xiaozhi.modules.security.service.impl;

import java.io.IOException;
import java.time.Duration;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import com.google.common.cache.Cache;
import com.google.common.cache.CacheBuilder;
import com.wf.captcha.SpecCaptcha;
import com.wf.captcha.base.Captcha;

import cn.hutool.core.util.RandomUtil;
import jakarta.annotation.Resource;
import jakarta.servlet.http.HttpServletResponse;
import xiaozhi.common.constant.Constant;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.security.service.CaptchaService;
import xiaozhi.modules.sms.service.SmsService;
import xiaozhi.modules.sys.service.SysParamsService;

/**
 * Mã xác minh
 */
@Service
public class CaptchaServiceImpl implements CaptchaService {
    @Resource
    private RedisUtils redisUtils;
    @Resource
    private SmsService smsService;
    @Resource
    private SysParamsService sysParamsService;
    @Value("${renren.redis.open}")
    private boolean open;
    /**
     * Bộ đệm cục bộ sẽ hết hạn sau 5 phút
     */
    Cache<String, String> localCache = CacheBuilder.newBuilder().maximumSize(1000)
            .expireAfterAccess(Duration.ofMinutes(5)).build();

    @Override
    public void create(HttpServletResponse response, String uuid) throws IOException {
        response.setContentType("image/gif");
        response.setHeader("Pragma", "No-cache");
        response.setHeader("Cache-Control", "no-cache");
        response.setDateHeader("Expires", 0);

        // Tạo mã xác minh
        SpecCaptcha captcha = new SpecCaptcha(150, 40);
        captcha.setLen(5);
        captcha.setCharType(Captcha.TYPE_DEFAULT);
        captcha.out(response.getOutputStream());

        // Lưu vào bộ đệm
        setCache(uuid, captcha.text());
    }

    @Override
    public boolean validate(String uuid, String code, Boolean delete) {
        if (StringUtils.isBlank(code)) {
            return false;
        }
        // Nhận mã xác minh
        String captcha = getCache(uuid, delete);

        // Đã thử nghiệm thành công
        if (code.equalsIgnoreCase(captcha)) {
            return true;
        }

        return false;
    }

    @Override
    public void sendSMSValidateCode(String phone) {
        // Kiểm tra khoảng thời gian gửi
        String lastSendTimeKey = RedisKeys.getSMSLastSendTimeKey(phone);
        // Nhận xem nó đã được gửi chưa, nếu thời gian gửi cuối cùng (60 giây) không được đặt
        String lastSendTime = redisUtils
                .getKeyOrCreate(lastSendTimeKey,
                        String.valueOf(System.currentTimeMillis()), 60L);
        if (lastSendTime != null) {
            long lastSendTimeLong = Long.parseLong(lastSendTime);
            long currentTime = System.currentTimeMillis();
            long timeDiff = currentTime - lastSendTimeLong;
            if (timeDiff < 60000) {
                throw new RenException(ErrorCode.SMS_SEND_TOO_FREQUENTLY, String.valueOf((60000 - timeDiff) / 1000));
            }
        }

        // Kiểm tra số lần gửi hôm nay
        String todayCountKey = RedisKeys.getSMSTodayCountKey(phone);
        Integer todayCount = (Integer) redisUtils.get(todayCountKey);
        if (todayCount == null) {
            todayCount = 0;
        }

        // Nhận giới hạn gửi tối đa
        Integer maxSendCount = sysParamsService.getValueObject(
                Constant.SysMSMParam.SERVER_SMS_MAX_SEND_COUNT.getValue(),
                Integer.class);
        if (maxSendCount == null) {
            maxSendCount = 5; // Giá trị mặc định
        }

        if (todayCount >= maxSendCount) {
            throw new RenException(ErrorCode.TODAY_SMS_LIMIT_REACHED);
        }

        String key = RedisKeys.getSMSValidateCodeKey(phone);
        String validateCodes = RandomUtil.randomNumbers(6);

        // Đặt mã xác minh
        setCache(key, validateCodes);

        // Cập nhật số lần gửi hôm nay
        if (todayCount == 0) {
            redisUtils.increment(todayCountKey, RedisUtils.DEFAULT_EXPIRE);
        } else {
            redisUtils.increment(todayCountKey);
        }

        // Gửi SMS mã xác minh
        smsService.sendVerificationCodeSms(phone, validateCodes);
    }

    @Override
    public boolean validateSMSValidateCode(String phone, String code, Boolean delete) {
        String key = RedisKeys.getSMSValidateCodeKey(phone);
        return validate(key, code, delete);
    }

    private void setCache(String key, String value) {
        if (open) {
            key = RedisKeys.getCaptchaKey(key);
            // Đặt hết hạn sau 5 phút
            redisUtils.set(key, value, 300);
        } else {
            localCache.put(key, value);
        }
    }

    private String getCache(String key, Boolean delete) {
        if (open) {
            key = RedisKeys.getCaptchaKey(key);
            String captcha = (String) redisUtils.get(key);
            // Xóa mã xác minh
            if (captcha != null && delete) {
                redisUtils.delete(key);
            }

            return captcha;
        }

        String captcha = localCache.getIfPresent(key);
        // Xóa mã xác minh
        if (captcha != null) {
            localCache.invalidate(key);
        }
        return captcha;
    }
}

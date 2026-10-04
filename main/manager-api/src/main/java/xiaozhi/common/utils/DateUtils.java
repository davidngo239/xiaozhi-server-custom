package xiaozhi.common.utils;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.Date;

/**
 * Xử lý ngày
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class DateUtils {
    /**
     * Định dạng thời gian (yyyy-MM-dd)
     */
    public final static String DATE_PATTERN = "yyyy-MM-dd";
    /**
     * Định dạng thời gian (yyyy-MM-dd HH:mm:ss)
     */
    public final static String DATE_TIME_PATTERN = "yyyy-MM-dd HH:mm:ss";
    public final static String DATE_TIME_MILLIS_PATTERN = "yyyy-MM-dd HH:mm:ss.SSS";


    /**
     * Định dạng ngày Định dạng ngày là: yyyy-MM-dd
     *
     * @param date Ngày
     * @return Trả về ngày ở định dạng yyyy-MM-dd
     */
    public static String format(Date date) {
        return format(date, DATE_PATTERN);
    }

    /**
     * Định dạng ngày Định dạng ngày là: yyyy-MM-dd
     *
     * @param date Ngày
     * @param pattern Định dạng, chẳng hạn như: DateUtils.DATE_TIME_PATTERN
     * @return Trả về ngày ở định dạng yyyy-MM-dd
     */
    public static String format(Date date, String pattern) {
        if (date != null) {
            SimpleDateFormat df = new SimpleDateFormat(pattern);
            return df.format(date);
        }
        return null;
    }

    /**
     * Phân tích ngày
     *
     * @param date Ngày
     * @param pattern Định dạng, chẳng hạn như: DateUtils.DATE_TIME_PATTERN
     * @return Ngày trở về
     */
    public static Date parse(String date, String pattern) {
        try {
            return new SimpleDateFormat(pattern).parse(date);
        } catch (ParseException e) {
            e.printStackTrace();
        }
        return null;
    }


    public static String getDateTimeNow() {
        return getDateTimeNow(DATE_TIME_PATTERN);
    }

    public static String getDateTimeNow(String pattern) {
        return format(new Date(), pattern);
    }

    public static String millsToSecond(long mills) {
        return String.format("%.3f", mills / 1000.0);
    }

    /**
     * Lấy chuỗi thời gian ngắn: 10 giây trước, quay lại ngay bây giờ, bao nhiêu giây trước, vài giờ trước, hơn một tuần, trả về năm, tháng, ngày, giờ, phút và giây
     * @param date
     * @return
     */
    public static String getShortTime(Date date) {
        if (date == null) {
            return null;
        }
        // Chuyển đổi ngày thành tức thì
        LocalDateTime localDateTime = date.toInstant()
                // Lấy múi giờ mặc định của hệ thống
                .atZone(ZoneId.systemDefault())
                // Chuyển đổi sang LocalDateTime
                .toLocalDateTime();
        // thời điểm hiện tại
        LocalDateTime now = LocalDateTime.now();
        // Chênh lệch thời gian tính bằng giây
        long secondsBetween = ChronoUnit.SECONDS.between(localDateTime, now);

        if (secondsBetween <= 10) {
            return "刚刚";
        } else if (secondsBetween < 60) {
            return secondsBetween + "秒前";
        } else if (secondsBetween < 60 * 60) {
            return secondsBetween / 60 + "分钟前";
        } else if (secondsBetween < 86400) {
            return secondsBetween / 3600 + "小时前";
        } else if (secondsBetween < 604800) {
            return secondsBetween / 86400 + "天前";
        } else {
            // Hơn một tuần, hiển thị đầy đủ ngày giờ
            return format(date,DATE_TIME_PATTERN);
        }
    }
}

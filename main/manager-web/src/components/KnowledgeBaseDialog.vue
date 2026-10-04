<template>
  <CustomDialog :title="title" :visible.sync="dialogVisible" width="600px" class="knowledge-base-dialog" @close="handleClose" @confirm="handleSubmit">
    <el-form ref="knowledgeBaseForm" :model="form" :rules="rules" label-width="100px" size="medium">
      <el-form-item :label="$t('knowledgeBaseDialog.name')" prop="name">
        <el-input v-model="form.name" :placeholder="$t('knowledgeBaseDialog.namePlaceholder')" clearable></el-input>
      </el-form-item>
      <el-form-item :label="$t('knowledgeBaseDialog.description')" prop="description">
        <el-input v-model="form.description" :placeholder="$t('knowledgeBaseDialog.descriptionPlaceholder')"
          type="textarea" :rows="4" maxlength="300" show-word-limit></el-input>
      </el-form-item>
      <el-form-item :label="$t('knowledgeBaseDialog.ragModel')" prop="ragModelId">
        <el-select v-model="form.ragModelId" :placeholder="$t('knowledgeBaseDialog.ragModelPlaceholder')" clearable
          filterable style="width: 100%" @focus="loadRAGModels">
          <el-option v-for="model in ragModels" :key="model.id" :label="$systemText(model.modelName)" :value="model.id">
          </el-option>
        </el-select>
      </el-form-item>
    </el-form>
  </CustomDialog>
</template>

<script>
import Api from "@/apis/api";
import CustomDialog from "./CustomDialog.vue";

export default {
  name: "KnowledgeBaseDialog",
  props: {
    title: {
      type: String,
      default: ""
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        datasetId: null,
        ragModelId: null,
        name: "",
        description: ""
      })
    }
  },
  data() {
    return {
      dialogVisible: this.visible,
      ragModels: [],
      rules: {
        name: [
          {
            required: true,
            message: this.$t("knowledgeBaseDialog.nameRequired"),
            trigger: "blur"
          },
          {
            min: 1,
            max: 50,
            message: this.$t("knowledgeBaseDialog.nameLength"),
            trigger: "blur"
          },
          {
            pattern: /^[\u4e00-\u9fa5a-zA-Z0-9\s-_]+$/,
            message: this.$t("knowledgeBaseDialog.namePattern"),
            trigger: "blur"
          }
        ],
        description: [
          {
            required: true,
            message: this.$t("knowledgeBaseDialog.descriptionRequired"),
            trigger: "blur"
          },
          {
            max: 300,
            message: this.$t("knowledgeBaseDialog.descriptionLength"),
            trigger: "blur"
          }
        ],
        ragModelId: [
          {
            required: true,
            message: this.$t("knowledgeBaseDialog.ragModelRequired"),
            trigger: "change"
          }
        ]
      }
    };
  },
  components: {
    CustomDialog
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
      if (val) {
        // Tải danh sách model RAG khi hộp thoại hiển thị
        this.loadRAGModels();

        // Nếu cơ sở kiến thức mới được thêm vào và ragModelId không được đặt thì mô hình RAG đầu tiên sẽ được chọn theo mặc định.
        if (!this.form.id && !this.form.ragModelId && this.ragModels.length > 0) {
          this.$set(this.form, 'ragModelId', this.ragModels[0].id);
        }

        if (this.$refs.knowledgeBaseForm) {
          this.$refs.knowledgeBaseForm.clearValidate();
        }
      }
    },
    // Theo dõi các thay đổi trong danh sách mô hình RAG để đảm bảo rằng các giá trị mặc định được đặt chính xác khi thực hiện bổ sung mới.
    ragModels(newModels) {
      if (newModels.length > 0) {
        // Nếu cơ sở kiến thức mới được thêm vào và ragModelId không được đặt thì mô hình RAG đầu tiên sẽ được chọn theo mặc định.
        if (!this.form.id && !this.form.ragModelId) {
          this.$set(this.form, 'ragModelId', newModels[0].id);
        }
      }
    }
  },
  methods: {
    handleClose() {
      // Không đặt lại các trường biểu mẫu để các lựa chọn trước đó được giữ lại khi chỉnh sửa
      // Chỉ đặt lại trạng thái xác thực khi hộp thoại đóng
      if (this.$refs.knowledgeBaseForm) {
        this.$refs.knowledgeBaseForm.clearValidate();
      }
      this.dialogVisible = false;
      this.$emit("update:visible", false);
    },
    handleSubmit() {
      console.log('KnowledgeBaseDialog handleSubmit called');
      this.$refs.knowledgeBaseForm.validate(valid => {
        console.log('Form validation result:', valid);
        if (valid) {
          console.log('Emitting submit event with form:', this.form);
          this.$emit("submit", {
            ...this.form
          });
        }
      });
    },
    loadRAGModels() {
      if (this.ragModels.length > 0) {
        return; // Đã tải rồi, tránh tải lặp lại
      }

      console.log('开始加载RAG模型列表');
      Api.model.getRAGModels((res) => {
        console.log('RAG模型列表响应:', res);
        if (res.data && res.data.code === 0) {
          this.ragModels = res.data.data || [];
          console.log('RAG模型列表加载成功，共', this.ragModels.length, '个模型');

          // Nếu cơ sở kiến thức mới được thêm vào và ragModelId không được đặt thì mô hình RAG đầu tiên sẽ được chọn theo mặc định.
          if (!this.form.id && !this.form.ragModelId && this.ragModels.length > 0) {
            this.$set(this.form, 'ragModelId', this.ragModels[0].id);
            console.log('已设置默认RAG模型:', this.ragModels[0].id);
          }
        } else {
          console.error('获取RAG模型列表失败:', res.data?.msg);
          this.$message.error(this.$t('knowledgeBaseDialog.loadRAGModelsFailed'));
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.knowledge-base-dialog {
  ::v-deep .el-dialog {
    border-radius: 20px;
    overflow: hidden;
  }

  ::v-deep .el-dialog__body {
    padding: 20px 30px;
  }

  ::v-deep .el-form-item {
    margin-bottom: 20px;
  }

  ::v-deep .el-form-item__label {
    font-weight: 500;
    color: #34495e;
    font-size: 14px;
  }

  ::v-deep .el-input {
    .el-input__inner {
      height: 36px;
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  ::v-deep .el-textarea {
    .el-textarea__inner {
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  ::v-deep .el-select {
    .el-input__inner {
      height: 36px;
      font-size: 14px;
      border-radius: 4px;
      border: 1px solid #ddd;
      transition: all 0.3s ease;

      &:focus {
        border-color: #5f70f3;
        box-shadow: 0 0 0 2px rgba(95, 112, 243, 0.2);
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}
</style>

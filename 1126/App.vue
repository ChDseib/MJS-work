<template>
  <div id="app" class="container">
    <h2 class="title">分类多选下拉菜单</h2>

    <el-form :model="form" label-width="120px">
      <el-row :gutter="20">
        <!-- 一级分类选择器 -->
        <el-col :span="12">
          <el-form-item label="一级分类">
            <el-select
                v-model="form.selectedCategories"
                multiple
                filterable
                clearable
                placeholder="请选择一级分类"
                @change="handleCategoryChange"
                style="width: 100%;">
              <el-option
                  v-for="category in categories"
                  :key="category.value"
                  :label="category.label"
                  :value="category.value">
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>

        <!-- 二级选项选择器 -->
        <el-col :span="12">
          <el-form-item label="二级选项">
            <el-select
                v-model="form.selectedItems"
                multiple
                filterable
                clearable
                placeholder="请选择二级选项"
                style="width: 100%;">
              <el-option
                  v-for="item in filteredItems"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value">
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
    </el-form>

    <!-- 显示选中的项 -->
    <div class="selected-tags">
      <h3>选中的分类:</h3>
      <el-tag
          v-for="item in selectedTags"
          :key="item.value"
          type="info"
          closable
          @close="removeTag(item.value)"
          style="margin-right: 5px; margin-bottom: 5px;">
        {{ item.label }}
      </el-tag>
    </div>
  </div>
</template>

<script>
import { ref, computed } from 'vue'

export default {
  name: 'App',
  setup() {
    // 定义一级分类数据
    const categories = [
      {
        label: '生活用品',
        value: 'living',
        children: [
          {label: '牙刷', value: 'toothbrush'},
          {label: '毛巾', value: 'towel'},
          {label: '肥皂', value: 'soap'},
          {label: '洗发水', value: 'shampoo'},
          {label: '沐浴露', value: 'body_wash'},
        ]
      },
      {
        label: '食物',
        value: 'food',
        children: [
          {label: '苹果', value: 'apple'},
          {label: '面包', value: 'bread'},
          {label: '牛奶', value: 'milk'},
          {label: '鸡蛋', value: 'eggs'},
          {label: '香蕉', value: 'banana'},
        ]
      },
      {
        label: '电子产品',
        value: 'electronics',
        children: [
          {label: '手机', value: 'phone'},
          {label: '电脑', value: 'computer'},
          {label: '耳机', value: 'earphones'},
          {label: '平板', value: 'tablet'},
          {label: '智能手表', value: 'smart_watch'},
        ]
      },
      // 更多一级分类
    ]

    // 表单数据
    const form = ref({
      selectedCategories: [],
      selectedItems: []
    })

    // 根据选中的一级分类过滤二级选项
    const filteredItems = computed(() => {
      let items = []
      categories.forEach(category => {
        if (form.value.selectedCategories.includes(category.value)) {
          items = items.concat(category.children)
        }
      })
      return items
    })

    // 处理一级分类变化
    const handleCategoryChange = () => {
      // 当一级分类变化时，过滤掉不属于选中分类的二级选项
      form.value.selectedItems = form.value.selectedItems.filter(item =>
          filteredItems.value.some(filteredItem => filteredItem.value === item)
      )
    }

    // 根据选中的二级选项获取标签
    const selectedTags = computed(() => {
      let tags = []
      categories.forEach(category => {
        category.children.forEach(child => {
          if (form.value.selectedItems.includes(child.value)) {
            tags.push({label: child.label, value: child.value})
          }
        })
      })
      return tags
    })

    // 移除标签时，从选中项中移除
    const removeTag = (value) => {
      const index = form.value.selectedItems.indexOf(value)
      if (index > -1) {
        form.value.selectedItems.splice(index, 1)
      }
    }

    return {
      categories,
      form,
      filteredItems,
      handleCategoryChange,
      selectedTags,
      removeTag
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.selected-tags {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  margin-top: 20px;
}

.selected-tags h3 {
  margin-bottom: 10px;
  color: #555;
}

.el-tag {
  cursor: pointer;
}
</style>
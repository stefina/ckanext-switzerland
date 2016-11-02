Vue.config.delimiters = ['[[', ']]'];
Vue.config.unsafeDelimiters = ['[[[', ']]]'];

new Vue({
  el: '#app',
  data: {
    currentSearchTerm: '',
    searchTerm: '',
    pageResults: [],
    datasetResults: [],
    language: '',
    loading: false,
    paginatePages: {
      currentPage: 1,
      itemsPerPage: 8,
      resultCount: 0
    },
    paginateDatasets: {
      currentPage: 1,
      itemsPerPage: 5,
      resultCount: 0
    }
  },
  computed: {
      totalPages: function() {
        return Math.ceil(this.paginatePages.resultCount / this.paginatePages.itemsPerPage)
      },
      totalDatasets: function() {
        return Math.ceil(this.paginateDatasets.resultCount / this.paginateDatasets.itemsPerPage)
      }
  },
  ready: function() {
    var self = this
    var lang = $('html').attr('lang')
    this.language = lang ? lang.split('-')[0] : 'en'

    var queryString = window.location.search
    if (queryString) {
      $.each(queryString.substring(1).split('&'), function(index, param) {
        var pair = param.split('=')
        if (pair[0] == 'q') {
          self.searchTerm = decodeURIComponent(pair[1])
          if (self.searchTerm.length >= 3) {
            self.search()
          }
        }
      })
    }
  },
  methods: {
    search: function() {
      var self = this

      this.loading = true

      var ckanSearch = $.ajax('/api/3/action/package_search?facet.limit=100&q=' + this.searchTerm)
      var wordPressSearch = $.ajax('/wp-json/wp/v2/pages/?filter[s]=' + this.searchTerm + '&per_page=100')

      $.when(ckanSearch, wordPressSearch).done(function(datasets, pages) {
        // ckan search results
        self.datasetResults = []
        datasets[0].result.results.map(function(result) {
          self.datasetResults.push({
            title: result.title[self.language],
            description: result.description[self.language],
            link: '/' + self.language + '/dataset/' + result.name
          })
        })

        // wordpress search results
        self.pageResults = []
        pages[0].map(function(result) {
          self.pageResults.push({
            title: result.title.rendered,
            description: result.excerpt.rendered,
            link: result.link
          })
        })

        self.currentSearchTerm = self.searchTerm
        self.loading = false
      })
    },
    setPage: function(pageNumber, paginate) {
      paginate.currentPage = pageNumber
    }
  },
  filters: {
    paginate: function(list, paginate) {
      paginate.resultCount = list.length;
      if (paginate == this.paginatePages && paginate.currentPage >= this.totalPages) {
        paginate.currentPage = this.totalPages
      }
      else if (paginate == this.paginateDatasets && paginate.currentPage >= this.totalDatasets) {
        paginate.currentPage = this.totalDatasets
      }
      var index = paginate.currentPage * paginate.itemsPerPage
      console.log(index);
      return list.slice(index, index + paginate.itemsPerPage)
    }
  }
})
